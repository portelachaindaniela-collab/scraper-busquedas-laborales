"""Orquestador. Se ejecuta con:  python -m scraper.main

Flujo:
  1. Lee config/busquedas.yml y config/filtros.yml.
  2. Por cada portal activo y cada término, trae los avisos de la ventana.
     Si un portal falla, se registra en el log y se sigue con los demás.
  3. Deduplica (dentro de la corrida y contra data/vistos.json).
  4. Aplica el filtro de descarte.
  5. Escribe data/ y docs/ (avisos.json, descartados.json, ultima_corrida.json).
"""
from __future__ import annotations

import datetime as dt
import re
import traceback

from . import almacenamiento as store
from . import config
from .filtros import evaluar
from .modelo import normalizar_texto
from .portales.bumeran import Bumeran
from .portales.computrabajo import Computrabajo
from .portales.linkedin import LinkedIn
from .portales.weremoto import Weremoto


def _construir_portales(bq: dict) -> dict:
    wr = bq.get("weremoto") or {}
    disponibles = {
        "bumeran": lambda: Bumeran(),
        "computrabajo": lambda: Computrabajo(),
        "weremoto": lambda: Weremoto(wr.get("categorias"), wr.get("palabras_clave")),
        "linkedin": lambda: LinkedIn(),
    }
    activos = bq.get("portales") or {}
    return {n: f for n, f in disponibles.items() if activos.get(n)}


def main() -> None:
    bq = config.busquedas()
    fl = config.filtros()
    terminos = bq.get("terminos") or []
    ventana = int(bq.get("ventana_horas", 48))
    ahora = dt.datetime.now()
    desde = ahora - dt.timedelta(hours=ventana)

    corrida = {
        "inicio": ahora.isoformat(),
        "ventana_horas": ventana,
        "terminos": terminos,
        "portales": {},
    }

    crudos: list = []
    for nombre, fabrica in _construir_portales(bq).items():
        info = {"estado": "ok", "encontrados": 0, "errores": []}
        try:
            portal = fabrica()
        except Exception as e:  # noqa: BLE001
            info["estado"] = "error"
            info["errores"].append(f"init: {e}")
            corrida["portales"][nombre] = info
            print(f"[ERROR] {nombre}: no se pudo inicializar: {e}")
            continue

        for termino in terminos:
            try:
                res = portal.buscar(termino, desde)
                info["encontrados"] += len(res)
                crudos.extend(res)
                print(f"[ok] {nombre} / {termino}: {len(res)}")
            except Exception as e:  # noqa: BLE001
                info["errores"].append(f"{termino}: {e}")
                print(f"[warn] {nombre} / {termino}: {e}")

        if info["errores"]:
            info["estado"] = "error" if info["encontrados"] == 0 else "parcial"
        corrida["portales"][nombre] = info

    ok, descartados = _procesar(crudos, fl, desde, ahora)

    corrida.update(
        {
            "fin": dt.datetime.now().isoformat(),
            "nuevos_totales": len(ok) + len(descartados),
            "publicados": len(ok),
            "descartados": len(descartados),
        }
    )

    store.guardar_resultados(ok, descartados, corrida)
    print(f"\nListo: {len(ok)} publicados, {len(descartados)} descartados.")
    for nombre, info in corrida["portales"].items():
        print(f"  {nombre}: {info['estado']} ({info['encontrados']} traídos)")


def _clave_dedup(aviso) -> str:
    """Colapsa repostings casi idénticos: misma empresa + título sin códigos de referencia."""
    titulo = re.sub(r"^(ref\.?\s*n?º?\.?\s*\d+[:.\-]?\s*)+", "", normalizar_texto(aviso.titulo))
    return f"{normalizar_texto(aviso.empresa)}|{titulo[:40]}"


def _procesar(crudos: list, fl: dict, desde: dt.datetime, ahora: dt.datetime):
    vistos = store.cargar_vistos()
    ok: list = []
    descartados: list = []
    nuevos_ids: set[str] = set()
    claves_dedup: set[str] = set()

    for aviso in crudos:
        if aviso.id in vistos or aviso.id in nuevos_ids:
            continue
        nuevos_ids.add(aviso.id)
        vistos[aviso.id] = ahora.isoformat()  # marcado como visto aunque después se descarte

        clave = _clave_dedup(aviso)
        if clave in claves_dedup:
            continue
        claves_dedup.add(clave)

        # descarte tardío por fecha: sólo si el aviso trae fecha y quedó fuera de ventana
        if aviso.fecha_publicacion:
            try:
                if dt.datetime.fromisoformat(aviso.fecha_publicacion) < desde:
                    continue
            except ValueError:
                pass

        aviso.capturado = ahora.isoformat()

        registro = aviso.to_dict()
        motivos = evaluar(aviso, fl)
        if motivos:
            registro["motivos_descarte"] = motivos
            descartados.append(registro)
        else:
            ok.append(registro)

    store.guardar_vistos(vistos)
    return ok, descartados


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - que el log del workflow muestre el traceback completo
        traceback.print_exc()
        raise
