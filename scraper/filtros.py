"""Motor del filtro de descarte. Las reglas viven en config/filtros.yml."""
from __future__ import annotations

from .modelo import Aviso, normalizar_texto


def evaluar(aviso: Aviso, cfg: dict) -> list[str]:
    """Devuelve la lista de motivos por los que el aviso se descarta.

    Lista vacía  => el aviso pasa el filtro.
    """
    motivos: list[str] = []
    texto = aviso.texto_para_filtro()
    perdones = [normalizar_texto(p) for p in cfg.get("frases_perdon", [])]

    for etiqueta, frases in (cfg.get("frases_excluyentes") or {}).items():
        for frase in frases or []:
            f = normalizar_texto(frase)
            if not f:
                continue
            idx = texto.find(f)
            if idx == -1:
                continue
            if _perdon_cerca(texto, idx, len(f), perdones):
                continue
            motivos.append(f"{etiqueta}: «{frase}»")
            break  # un motivo por etiqueta alcanza

    if not _ubicacion_ok(aviso, cfg):
        motivos.append(f"ubicacion fuera de zona: «{aviso.ubicacion or 's/d'}»")

    return motivos


def _perdon_cerca(texto: str, idx: int, largo: int, perdones: list[str], ventana: int = 70) -> bool:
    ini = max(0, idx - ventana)
    fin = idx + largo + ventana
    ctx = texto[ini:fin]
    return any(p and p in ctx for p in perdones)


# Frases que en la descripción sí alcanzan para considerar el aviso remoto
# (un "remoto" suelto en el cuerpo no alcanza; "híbrido" tampoco es remoto).
_REMOTO_FUERTE = (
    "100% remoto", "100 % remoto", "100 remoto", "totalmente remoto",
    "completamente remoto", "full remote", "fully remote", "100% remote",
    "trabajo remoto", "modalidad remota", "work from anywhere", "desde cualquier lugar",
)


def _es_remoto(aviso: Aviso, cfg: dict) -> bool:
    if normalizar_texto(aviso.modalidad) == "remoto":
        return True
    indicadores = [normalizar_texto(x) for x in cfg.get("indicadores_remoto", [])]
    campos = normalizar_texto(" ".join(x for x in (aviso.ubicacion, aviso.titulo) if x))
    if any(x in campos for x in indicadores):
        return True
    desc = normalizar_texto(aviso.descripcion or "")
    return any(f in desc for f in _REMOTO_FUERTE)


def _ubicacion_ok(aviso: Aviso, cfg: dict) -> bool:
    if _es_remoto(aviso, cfg):
        return True
    u = normalizar_texto(aviso.ubicacion)
    if not u:
        return False  # sin ubicación y sin señal de remoto => se descarta (regla: no inventar)

    excluidas = [normalizar_texto(x) for x in cfg.get("ubicaciones_excluidas", [])]
    if any(e and e in u for e in excluidas):
        return False  # el interior / GBA sur-oeste gana aunque diga "Argentina"

    permitidas = [normalizar_texto(x) for x in cfg.get("ubicaciones_permitidas", [])]
    return any(p and p in u for p in permitidas)
