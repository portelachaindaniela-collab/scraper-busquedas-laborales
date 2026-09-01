"""Chequeo de relevancia para portales con búsqueda difusa (Computrabajo).

Computrabajo devuelve muchos avisos apenas relacionados con el término
(p. ej. "comunicación digital" trae "Asistente de Atención al Cliente").
Esto exige que el título mencione alguna palabra significativa del término.
"""
from __future__ import annotations

from .modelo import normalizar_texto

_STOP = {
    "de", "del", "la", "el", "los", "las", "y", "o", "para", "con", "en",
    "analista", "digital", "manager", "sr", "ssr", "jr", "senior", "junior", "semi",
}


def palabras_clave(termino: str) -> list[str]:
    return [w for w in normalizar_texto(termino).split() if len(w) >= 4 and w not in _STOP]


def es_relevante(texto: str, termino: str) -> bool:
    claves = palabras_clave(termino)
    if not claves:
        return True
    t = normalizar_texto(texto)
    return any(k in t or k.rstrip("s") in t for k in claves)
