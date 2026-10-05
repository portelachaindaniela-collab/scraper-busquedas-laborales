"""Indeed Argentina — best-effort.

No hay API pública. Se pide el listado de https://ar.indeed.com/jobs y se lee
el JSON que la página trae embebido para dibujar las tarjetas
(window.mosaic.providerData["mosaic-provider-jobcards"]). Si no está, se leen
las tarjetas del HTML.

Indeed bloquea fuerte el tráfico automatizado (Cloudflare / hCaptcha). Ante un
challenge o un código distinto de 200 se lanza PortalError, se registra y se
sigue con el resto, igual que LinkedIn. Los avisos traen sólo un fragmento de
la descripción (snippet), así que el filtro mira poco texto.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import time

from bs4 import BeautifulSoup

from ..http import crear_sesion, get
from ..modelo import Aviso
from ..relevancia import es_relevante
from .base import PortalError, limpiar_html

BASE = "https://ar.indeed.com"
LISTADO = BASE + "/jobs"
URL_AVISO = BASE + "/viewjob?jk={jk}"
PAGE_SIZE = 10
MAX_PAGINAS = 3
PAUSA = 2.0
FILTRO_REMOTO = "0kf:attr(DSQF7);"
_MARCA_BLOQUEO = ("just a moment", "security check", "verify you are human", "hcaptcha", "cf-chl")
_MARCA_JSON = 'window.mosaic.providerData["mosaic-provider-jobcards"]'


class Indeed:
    nombre = "indeed"

    def __init__(self, ubicaciones: list[str] | None = None, incluir_remotos: bool = True) -> None:
        self.s = crear_sesion()
        self.s.headers["Referer"] = BASE + "/"
        self.ubicaciones = ubicaciones or ["Buenos Aires"]
        self.incluir_remotos = incluir_remotos

    def buscar(self, termino: str, desde: dt.datetime) -> list[Aviso]:
        horas = (dt.datetime.now() - desde).total_seconds() / 3600
        fromage = max(1, math.ceil(horas / 24))

        consultas = [{"q": termino, "l": lugar, "fromage": fromage} for lugar in self.ubicaciones]
        if self.incluir_remotos:
            consultas.append({"q": termino, "fromage": fromage, "sc": FILTRO_REMOTO})

        avisos: list[Aviso] = []
        vistos: set[str] = set()
        for params in consultas:
            for page in range(MAX_PAGINAS):
                if page:
                    time.sleep(PAUSA)
                r = get(self.s, LISTADO, params={**params, "start": page * PAGE_SIZE})
                if r.status_code != 200:
                    raise PortalError(f"Indeed respondió HTTP {r.status_code}")
                if any(m in r.text.lower() for m in _MARCA_BLOQUEO):
                    raise PortalError("Indeed pidió verificación (posible bloqueo)")

                tarjetas = parsear(r.text)
                for av in tarjetas:
                    if av.portal_id in vistos:
                        continue
                    if not es_relevante(av.titulo, termino):
                        continue
                    if av.fecha_publicacion and dt.datetime.fromisoformat(av.fecha_publicacion) < desde:
                        continue
                    vistos.add(av.portal_id)
                    avisos.append(av)

                if len(tarjetas) < PAGE_SIZE:
                    break
        return avisos


def parsear(html: str) -> list[Aviso]:
    """Avisos de una página de resultados: primero el JSON embebido, si no las tarjetas del HTML."""
    resultados = _json_embebido(html)
    if resultados is not None:
        return [av for av in (_desde_json(j) for j in resultados) if av]
    return _desde_html(html)


def _json_embebido(html: str) -> list[dict] | None:
    i = html.find(_MARCA_JSON)
    if i < 0:
        return None
    i = html.find("{", i)
    if i < 0:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(html, i)
        return data["metaData"]["mosaicProviderJobCardsModel"]["results"]
    except (ValueError, KeyError, TypeError):
        return None


def _desde_json(j: dict) -> Aviso | None:
    jk = j.get("jobkey")
    if not jk:
        return None
    fecha = None
    if j.get("pubDate"):
        try:
            fecha = dt.datetime.fromtimestamp(int(j["pubDate"]) / 1000)
        except (ValueError, TypeError, OSError):
            pass
    salario = (j.get("salarySnippet") or {}).get("text") or None
    return Aviso(
        portal="indeed",
        portal_id=jk,
        titulo=(j.get("displayTitle") or j.get("title") or "(sin título)").strip(),
        empresa=j.get("company") or None,
        ubicacion=j.get("formattedLocation") or None,
        modalidad="remoto" if j.get("remoteLocation") is True else None,
        salario=salario,
        fecha_publicacion=fecha.replace(microsecond=0).isoformat() if fecha else None,
        url=URL_AVISO.format(jk=jk),
        descripcion=limpiar_html(j.get("snippet")),
    )


def _desde_html(html: str) -> list[Aviso]:
    avisos: list[Aviso] = []
    for a in BeautifulSoup(html, "lxml").select("a[data-jk]"):
        jk = a["data-jk"]
        tarjeta = a.find_parent("li") or a.find_parent("td") or a.parent
        titulo = a.select_one("span[title]")
        empresa = tarjeta.select_one('[data-testid="company-name"]')
        lugar = tarjeta.select_one('[data-testid="text-location"]')
        avisos.append(
            Aviso(
                portal="indeed",
                portal_id=jk,
                titulo=(titulo["title"] if titulo else a.get_text(" ", strip=True)) or "(sin título)",
                empresa=empresa.get_text(" ", strip=True) if empresa else None,
                ubicacion=lugar.get_text(" ", strip=True) if lugar else None,
                modalidad=None,
                salario=None,
                fecha_publicacion=None,
                url=URL_AVISO.format(jk=jk),
                descripcion=None,
            )
        )
    return avisos
