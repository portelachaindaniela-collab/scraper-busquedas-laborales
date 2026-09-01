"""Computrabajo Argentina.

No tiene API ni RSS. Se scrapea el HTML del listado (renderizado en servidor)
y, para cada aviso candidato, se lee el JSON-LD `JobPosting` de la página de
detalle (trae `description` y `datePosted`).

La búsqueda de Computrabajo es difusa: `/trabajo-de-<termino>` devuelve cientos
de avisos apenas relacionados. Por eso se filtra por relevancia sobre el título
ANTES de pedir el detalle de cada uno (así también se hacen muchos menos pedidos).

Computrabajo está detrás de Cloudflare: desde una IP de datacenter puede
responder con un challenge. Si eso pasa se lanza PortalError y el orquestador
sigue con los demás portales, dejando registro en el log.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time

from bs4 import BeautifulSoup

from ..http import crear_sesion, get
from ..modelo import Aviso, slugify
from ..relevancia import es_relevante
from .base import PortalError, limpiar_html

BASE = "https://ar.computrabajo.com"
LISTADO = BASE + "/trabajo-de-{slug}"
MAX_PAGINAS = 4
PAUSA_LISTADO = 1.5
PAUSA_DETALLE = 1.2

_RE_MIN = re.compile(r"hace\s+(\d+)\s+minuto")
_RE_HORAS = re.compile(r"hace\s+(\d+)\s+hora")
_RE_DIAS = re.compile(r"hace\s+(\d+)\s+d[ií]a")
_RE_SALARIO = re.compile(r"\$\s?[\d.]+")
_RE_RATING = re.compile(r"^\s*\d+[.,]\d+\s+")  # "4,4 Empresa SA" -> "Empresa SA"
_MARCA_CF = ("just a moment", "attention required", "cf-browser-verification")


class Computrabajo:
    nombre = "computrabajo"

    def __init__(self) -> None:
        self.s = crear_sesion()
        self.s.headers["Referer"] = BASE + "/"

    def buscar(self, termino: str, desde: dt.datetime) -> list[Aviso]:
        ahora = dt.datetime.now()
        slug = slugify(termino)
        candidatos: list[dict] = []

        for p in range(1, MAX_PAGINAS + 1):
            url = LISTADO.format(slug=slug) + (f"?p={p}" if p > 1 else "")
            r = get(self.s, url)
            if r.status_code == 404:
                break
            if r.status_code != 200 or any(m in r.text[:1500].lower() for m in _MARCA_CF):
                raise PortalError(f"HTTP {r.status_code} — posible bloqueo Cloudflare ({url})")

            articulos = BeautifulSoup(r.text, "lxml").select("article.box_offer")
            if not articulos:
                break

            for art in articulos:
                card = _parse_card(art, ahora)
                if not card:
                    continue
                if card["fecha"] and card["fecha"] < desde:
                    continue
                if not es_relevante(card["titulo"], termino):
                    continue
                candidatos.append(card)

            if len(articulos) < 20:  # última página
                break
            time.sleep(PAUSA_LISTADO)

        avisos: list[Aviso] = []
        for card in candidatos:
            descripcion, fecha_detalle = self._detalle(card["url"])
            fecha = card["fecha"] or fecha_detalle
            avisos.append(
                Aviso(
                    portal=self.nombre,
                    portal_id=card["id"],
                    titulo=card["titulo"],
                    empresa=card["empresa"],
                    ubicacion=card["ubicacion"],
                    modalidad=card["modalidad"],
                    salario=card["salario"],
                    fecha_publicacion=fecha.replace(microsecond=0).isoformat() if fecha else None,
                    url=card["url"],
                    descripcion=descripcion,
                )
            )
            time.sleep(PAUSA_DETALLE)
        return avisos

    def _detalle(self, url: str) -> tuple[str | None, dt.datetime | None]:
        try:
            r = get(self.s, url)
            if r.status_code != 200:
                return None, None
            soup = BeautifulSoup(r.text, "lxml")
            descripcion: str | None = None
            fecha: dt.datetime | None = None

            for sc in soup.select('script[type="application/ld+json"]'):
                try:
                    obj = json.loads(sc.string or "{}")
                except (ValueError, TypeError):
                    continue
                nodos = obj.get("@graph", [obj]) if isinstance(obj, dict) else []
                for nodo in nodos:
                    if not isinstance(nodo, dict) or nodo.get("@type") != "JobPosting":
                        continue
                    descripcion = limpiar_html(nodo.get("description")) or descripcion
                    dp = (nodo.get("datePosted") or "")[:10]
                    if dp:
                        try:
                            fecha = dt.datetime.fromisoformat(dp)
                        except ValueError:
                            pass

            if not descripcion:
                cont = soup.select_one("div.box_detail, .detail_of, div.mbB")
                descripcion = limpiar_html(str(cont)) if cont else None
            return descripcion, fecha
        except Exception:  # noqa: BLE001 - el detalle es best-effort
            return None, None


def _parse_card(art, ahora: dt.datetime) -> dict | None:
    a = art.select_one("h2 a.js-o-link") or art.select_one("h2 a")
    if not a or not a.get("href"):
        return None
    href = a["href"].split("#")[0]

    # La <p> de empresa lleva la clase dFlex; la de ubicación no.
    emp_a = art.select_one("a[offer-grid-article-company-url]")
    emp_p = art.select_one("p.dFlex.fc_base")
    if emp_a:
        empresa = emp_a.get_text(" ", strip=True)
    elif emp_p:
        empresa = _RE_RATING.sub("", emp_p.get_text(" ", strip=True)) or None
    else:
        empresa = None

    loc_p = art.select_one("p.fs16.fc_base.mt5:not(.dFlex)")
    ubicacion = loc_p.get_text(" ", strip=True) if loc_p else None

    modal_el = art.select_one("div.fs13 span.dIB")
    modal_txt = modal_el.get_text(" ", strip=True).lower() if modal_el else ""
    if "remoto" in modal_txt and "presencial" in modal_txt:
        modalidad = "hibrido"
    elif "remoto" in modal_txt:
        modalidad = "remoto"
    elif "hibrid" in modal_txt or "híbrid" in modal_txt:
        modalidad = "hibrido"
    elif "presencial" in modal_txt:
        modalidad = "presencial"
    else:
        modalidad = None

    fecha_el = art.select_one("p.fc_aux")
    sal_match = art.find(string=_RE_SALARIO)

    return {
        "id": art.get("data-id") or slugify(href),
        "titulo": a.get_text(" ", strip=True),
        "empresa": empresa,
        "ubicacion": ubicacion,
        "modalidad": modalidad,
        "salario": _RE_SALARIO.search(sal_match).group(0).strip() if sal_match else None,
        "fecha": _fecha_relativa(fecha_el.get_text(" ", strip=True), ahora) if fecha_el else None,
        "url": BASE + href if href.startswith("/") else href,
    }


def _fecha_relativa(txt: str, ahora: dt.datetime) -> dt.datetime | None:
    t = txt.strip().lower()
    if "hoy" in t or "instante" in t or "segundo" in t:
        return ahora
    if m := _RE_MIN.search(t):
        return ahora - dt.timedelta(minutes=int(m.group(1)))
    if m := _RE_HORAS.search(t):
        return ahora - dt.timedelta(hours=int(m.group(1)))
    if "ayer" in t:
        return ahora - dt.timedelta(hours=30)
    if m := _RE_DIAS.search(t):
        return ahora - dt.timedelta(days=int(m.group(1)))
    return None  # formato desconocido: que decida la ventana con fecha None
