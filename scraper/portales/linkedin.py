"""LinkedIn — best-effort.

No hay API pública. Se usa el endpoint "guest" que alimenta el listado sin login
(jobs-guest/.../seeMoreJobPostings/search) con el filtro de fecha f_TPR.

Es frágil: LinkedIn limita fuerte por IP y las de GitHub Actions están muy
usadas. Ante 429 / 999 se lanza PortalError, se registra y se sigue con el resto.
Los avisos vienen sin descripción, así que en LinkedIn el filtro sólo puede
mirar el título y la ubicación.
"""
from __future__ import annotations

import datetime as dt
import re

from bs4 import BeautifulSoup

from ..http import crear_sesion, get
from ..modelo import Aviso
from .base import PortalError

API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
UBICACION = "Argentina"
MAX_PAGINAS = 4
PAGE_SIZE = 25
_RE_ID = re.compile(r"-(\d+)(?:\?|$)")


class LinkedIn:
    nombre = "linkedin"

    def __init__(self) -> None:
        self.s = crear_sesion()
        self.s.headers["Referer"] = "https://www.linkedin.com/jobs"

    def buscar(self, termino: str, desde: dt.datetime) -> list[Aviso]:
        segundos = max(3600, int((dt.datetime.now() - desde).total_seconds()))
        avisos: list[Aviso] = []

        for page in range(MAX_PAGINAS):
            params = {
                "keywords": termino,
                "location": UBICACION,
                "f_TPR": f"r{segundos}",
                "start": page * PAGE_SIZE,
            }
            r = get(self.s, API, params=params)
            if r.status_code in (429, 999):
                raise PortalError(f"LinkedIn bloqueó (HTTP {r.status_code})")
            if r.status_code != 200:
                break

            tarjetas = BeautifulSoup(r.text, "lxml").select("li")
            if not tarjetas:
                break
            for li in tarjetas:
                aviso = _parse(li)
                if aviso:
                    avisos.append(aviso)
            if len(tarjetas) < PAGE_SIZE:
                break
        return avisos


def _parse(li) -> Aviso | None:
    a = li.select_one("a.base-card__full-link") or li.select_one('a[href*="/jobs/view/"]')
    if not a or not a.get("href"):
        return None
    url = a["href"].split("?")[0]
    m = _RE_ID.search(a["href"])

    titulo = li.select_one("h3")
    empresa = li.select_one("h4 a") or li.select_one(".base-search-card__subtitle")
    lugar = li.select_one(".job-search-card__location")
    time_el = li.select_one("time")
    fecha = None
    if time_el and time_el.get("datetime"):
        try:
            fecha = dt.datetime.fromisoformat(time_el["datetime"][:10])
        except ValueError:
            pass

    return Aviso(
        portal="linkedin",
        portal_id=m.group(1) if m else url.rsplit("/", 1)[-1],
        titulo=titulo.get_text(" ", strip=True) if titulo else "(sin título)",
        empresa=empresa.get_text(" ", strip=True) if empresa else None,
        ubicacion=lugar.get_text(" ", strip=True) if lugar else None,
        modalidad=None,
        salario=None,
        fecha_publicacion=fecha.isoformat() if fecha else None,
        url=url,
        descripcion=None,
    )
