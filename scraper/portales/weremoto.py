"""WeRemoto (weremoto.com) — trabajos remotos para Latinoamérica.

El sitio es Next.js con render en servidor: el listado de cada categoría trae
todos los avisos en el HTML, incluída la descripción completa (dentro de
<details>). No hay API ni RSS y no hace falta pedir la página de cada aviso.

Se navega por CATEGORÍA (no por término). Las categorías y las palabras clave
para quedarse sólo con lo relevante se configuran en config/busquedas.yml.

Nota: la mayoría de los avisos son de clientes de EE.UU. que piden inglés C1/C2;
el filtro de descarte por inglés se encarga de eso.
"""
from __future__ import annotations

import datetime as dt
import re

from bs4 import BeautifulSoup

from ..http import crear_sesion, get
from ..modelo import Aviso, normalizar_texto, slugify
from .base import PortalError, limpiar_html

BASE = "https://www.weremoto.com"
LISTADO = BASE + "/categoria-de-trabajo/{categoria}"

_MESES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12,
}
_RE_FECHA = re.compile(r"(\d{1,2})\s+([a-zñ]+)")


class Weremoto:
    nombre = "weremoto"

    def __init__(self, categorias: list[str] | None = None, palabras_clave: list[str] | None = None) -> None:
        self.s = crear_sesion()
        self.categorias = categorias or ["marketing", "contenido"]
        self.palabras_clave = [normalizar_texto(p) for p in (palabras_clave or [])]
        self._cache: list[Aviso] | None = None

    def buscar(self, termino: str, desde: dt.datetime) -> list[Aviso]:
        avisos = self._todos(desde)
        claves = self.palabras_clave or [normalizar_texto(termino)]
        return [av for av in avisos if _menciona(av, claves)]

    def _todos(self, desde: dt.datetime) -> list[Aviso]:
        if self._cache is not None:
            return self._cache

        ahora = dt.datetime.now()
        vistos: set[str] = set()
        avisos: list[Aviso] = []
        errores: list[str] = []

        for categoria in self.categorias:
            try:
                r = get(self.s, LISTADO.format(categoria=categoria))
                if r.status_code != 200:
                    errores.append(f"{categoria}: HTTP {r.status_code}")
                    continue
                soup = BeautifulSoup(r.text, "lxml")
                for art in soup.select("article"):
                    card = _parse_card(art, categoria, ahora)
                    if not card or card.portal_id in vistos:
                        continue
                    if card.fecha_publicacion and dt.datetime.fromisoformat(card.fecha_publicacion) < desde:
                        continue
                    vistos.add(card.portal_id)
                    avisos.append(card)
            except Exception as e:  # noqa: BLE001
                errores.append(f"{categoria}: {e}")

        if not avisos and errores:
            raise PortalError("; ".join(errores))

        self._cache = avisos
        return avisos


def _menciona(aviso: Aviso, claves: list[str]) -> bool:
    texto = normalizar_texto(" ".join(x for x in (aviso.titulo, aviso.descripcion) if x))
    return any(k and k in texto for k in claves)


def _parse_card(art, categoria: str, ahora: dt.datetime) -> Aviso | None:
    a = art.select_one('h3 a[href*="/job-posts/"]') or art.select_one('a[href*="/job-posts/"]')
    if not a or not a.get("href"):
        return None
    href = a["href"].split("?")[0]

    h3 = a.find_parent("h3")
    empresa_el = h3.find_next_sibling("p") if h3 else None

    spans = [s.get_text(" ", strip=True) for s in art.select("span")]
    loc_el = art.select_one("span.truncate")
    ubicacion = loc_el.get_text(" ", strip=True) if loc_el else next(
        (s for s in spans
         if s and not _RE_FECHA.search(s.lower()) and s.lower() not in ("full time", "part time")
         and "marketing" not in s.lower()),
        None,
    )
    fecha_txt = next((s for s in spans if len(s) <= 14 and _RE_FECHA.search(s.strip().lower())), None)
    detalle = art.select_one("details .article-body") or art.select_one("details")

    return Aviso(
        portal="weremoto",
        portal_id=href.rsplit("/", 1)[-1] or slugify(href),
        titulo=a.get_text(" ", strip=True),
        empresa=empresa_el.get_text(" ", strip=True) if empresa_el else None,
        ubicacion=ubicacion,
        modalidad="remoto",  # WeRemoto es un board 100% remoto
        salario=None,
        fecha_publicacion=_fecha(fecha_txt, ahora),
        url=BASE + href if href.startswith("/") else href,
        descripcion=limpiar_html(str(detalle)) if detalle else None,
    )


def _fecha(txt: str | None, ahora: dt.datetime) -> str | None:
    if not txt:
        return None
    m = _RE_FECHA.search(txt.strip().lower())
    if not m:
        return None
    dia = int(m.group(1))
    mes = _MESES.get(m.group(2)[:4]) or _MESES.get(m.group(2)[:3])
    if not mes:
        return None
    try:
        f = dt.datetime(ahora.year, mes, dia, 12, 0)
    except ValueError:
        return None
    if f - ahora > dt.timedelta(days=1):  # "dic" visto en enero => es del año pasado
        f = f.replace(year=ahora.year - 1)
    return f.isoformat()
