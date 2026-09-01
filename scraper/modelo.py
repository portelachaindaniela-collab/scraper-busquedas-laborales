"""Modelo de datos común a todos los portales."""
from __future__ import annotations

import dataclasses
import re
import unicodedata
from typing import Optional


def normalizar_texto(s: Optional[str]) -> str:
    """Minúsculas, sin acentos, espacios colapsados. Base para el matching de filtros."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def slugify(s: str) -> str:
    s = normalizar_texto(s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "aviso"


@dataclasses.dataclass
class Aviso:
    portal: str
    portal_id: str
    titulo: str
    empresa: Optional[str]
    ubicacion: Optional[str]
    modalidad: Optional[str]           # "remoto" | "presencial" | "hibrido" | None
    salario: Optional[str]
    fecha_publicacion: Optional[str]   # ISO 8601, o None si el aviso no lo trae
    url: str
    descripcion: Optional[str]
    capturado: str = ""               # ISO 8601, lo completa el orquestador

    @property
    def id(self) -> str:
        return f"{self.portal}:{self.portal_id}"

    def texto_para_filtro(self) -> str:
        partes = [self.titulo, self.descripcion, self.ubicacion, self.modalidad]
        return normalizar_texto(" ".join(p for p in partes if p))

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["id"] = self.id
        return d
