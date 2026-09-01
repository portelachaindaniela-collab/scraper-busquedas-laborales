"""Cliente HTTP compartido.

Usa curl_cffi imitando el handshake TLS de Chrome, que es lo que hace falta
para pasar la protección de Cloudflare de Computrabajo desde una IP de datacenter
(GitHub Actions). Incluye reintentos con backoff ante 429/403/503.
"""
from __future__ import annotations

import random
import time
from typing import Callable

from curl_cffi import requests as _cffi

IMPERSONATE = "chrome124"
ACCEPT_LANG = "es-AR,es;q=0.9,en;q=0.5"


def crear_sesion() -> "_cffi.Session":
    s = _cffi.Session(impersonate=IMPERSONATE, timeout=30)
    s.headers.update({"Accept-Language": ACCEPT_LANG})
    return s


class RespuestaBloqueada(Exception):
    pass


def _con_reintento(fn: Callable, intentos: int = 3, base: float = 2.5):
    ultimo = None
    for n in range(intentos):
        try:
            r = fn()
        except Exception as e:  # noqa: BLE001 - error de red; reintentamos
            ultimo = e
            time.sleep(base * (n + 1) + random.random())
            continue
        if r.status_code in (429, 403, 503):
            ultimo = RespuestaBloqueada(f"HTTP {r.status_code}")
            time.sleep(base * (n + 1) + random.random())
            continue
        return r
    if isinstance(ultimo, Exception):
        raise ultimo
    raise RespuestaBloqueada("agotados los reintentos")


def get(sesion, url: str, **kw):
    return _con_reintento(lambda: sesion.get(url, **kw))


def post(sesion, url: str, **kw):
    return _con_reintento(lambda: sesion.post(url, **kw))
