"""Bumeran Argentina.

No hay API pública documentada, pero el front del sitio usa un endpoint JSON
interno estable: POST /api/avisos/searchV2 con el header x-site-id: BMAR.
Devuelve la descripción completa en cada resultado, así que no hace falta
pedir la página de cada aviso.
"""
from __future__ import annotations

import datetime as dt
import uuid

from ..http import crear_sesion, post
from ..modelo import Aviso, slugify
from .base import PortalError, limpiar_html

API = "https://www.bumeran.com.ar/api/avisos/searchV2"
SITE_ID = "BMAR"
URL_AVISO = "https://www.bumeran.com.ar/empleos/{slug}-{pid}.html"  # el slug es cosmético; resuelve por id
PAGE_SIZE = 100
MAX_PAGINAS = 5

_MODALIDAD = {
    "remoto": "remoto",
    "presencial": "presencial",
    "hibrido": "hibrido",
    "híbrido": "hibrido",
}


class Bumeran:
    nombre = "bumeran"

    def __init__(self) -> None:
        self.s = crear_sesion()
        self.s.headers.update(
            {
                "x-site-id": SITE_ID,
                "x-pre-session-token": str(uuid.uuid4()),
                "Content-Type": "application/json",
                "Origin": "https://www.bumeran.com.ar",
                "Referer": "https://www.bumeran.com.ar/empleos.html",
            }
        )

    def buscar(self, termino: str, desde: dt.datetime) -> list[Aviso]:
        avisos: list[Aviso] = []
        for page in range(MAX_PAGINAS):
            url = f"{API}?pageSize={PAGE_SIZE}&page={page}&sort=RECIENTES"
            r = post(self.s, url, json={"filtros": [], "query": termino, "internacional": False})
            if r.status_code != 200:
                raise PortalError(f"HTTP {r.status_code} (página {page})")
            content = (r.json() or {}).get("content") or []
            if not content:
                break

            corta = False
            for c in content:
                fecha = _fecha(c)
                if fecha and fecha < desde:
                    corta = True  # RECIENTES viene ordenado desc: de acá para abajo es viejo
                    continue
                avisos.append(self._a_aviso(c, fecha))

            if corta or len(content) < PAGE_SIZE:
                break
        return avisos

    def _a_aviso(self, c: dict, fecha: dt.datetime | None) -> Aviso:
        pid = str(c.get("id"))
        titulo = (c.get("titulo") or "").strip()
        empresa = None if c.get("confidencial") else (c.get("empresa") or None)
        modalidad = _MODALIDAD.get((c.get("modalidadTrabajo") or "").strip().lower())
        return Aviso(
            portal=self.nombre,
            portal_id=pid,
            titulo=titulo,
            empresa=empresa,
            ubicacion=c.get("localizacion") or None,
            modalidad=modalidad,
            salario=None,  # el listado no expone el monto
            fecha_publicacion=fecha.isoformat() if fecha else None,
            url=URL_AVISO.format(slug=slugify(f"{titulo} {empresa or ''}"), pid=pid),
            descripcion=limpiar_html(c.get("detalle")),
        )


def _fecha(c: dict) -> dt.datetime | None:
    for campo, fmt in (
        ("fechaHoraPublicacion", "%d-%m-%Y %H:%M:%S"),
        ("fechaPublicacion", "%d-%m-%Y"),
    ):
        valor = (c.get(campo) or "").strip()
        if not valor:
            continue
        try:
            return dt.datetime.strptime(valor, fmt)
        except ValueError:
            continue
    return None
