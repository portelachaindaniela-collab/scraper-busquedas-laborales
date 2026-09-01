"""Lectura/escritura de los JSON: vistos, avisos publicados, descartados y log."""
from __future__ import annotations

import datetime as dt
import json
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
DOCS = RAIZ / "docs"

RETENCION_VISTOS_DIAS = 60      # cuánto recordamos un aviso para no repetirlo
RETENCION_PUBLICADOS_DIAS = 14  # cuánto queda un aviso en la lista de la web


def _leer(p: pathlib.Path, default):
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            return default
    return default


def _escribir(p: pathlib.Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def cargar_vistos() -> dict:
    return _leer(DATA / "vistos.json", {})


def guardar_vistos(vistos: dict) -> None:
    corte = (dt.datetime.now() - dt.timedelta(days=RETENCION_VISTOS_DIAS)).isoformat()
    _escribir(DATA / "vistos.json", {k: v for k, v in vistos.items() if v >= corte})


def cargar_publicados() -> list:
    return _leer(DATA / "avisos.json", [])


def guardar_resultados(nuevos_ok: list, nuevos_descartados: list, corrida: dict) -> None:
    corte = (dt.datetime.now() - dt.timedelta(days=RETENCION_PUBLICADOS_DIAS)).isoformat()

    ok = _combinar(cargar_publicados(), nuevos_ok, corte)
    _escribir(DATA / "avisos.json", ok)
    _escribir(DOCS / "avisos.json", ok)

    desc = _combinar(_leer(DATA / "descartados.json", []), nuevos_descartados, corte)
    _escribir(DATA / "descartados.json", desc)

    _escribir(DATA / "ultima_corrida.json", corrida)
    _escribir(DOCS / "ultima_corrida.json", corrida)


def _combinar(previos: list, nuevos: list, corte: str) -> list:
    ids_nuevos = {a["id"] for a in nuevos}
    conservados = [
        a for a in previos
        if a["id"] not in ids_nuevos and a.get("capturado", "") >= corte
    ]
    combinados = nuevos + conservados
    combinados.sort(
        key=lambda a: a.get("fecha_publicacion") or a.get("capturado") or "",
        reverse=True,
    )
    return combinados
