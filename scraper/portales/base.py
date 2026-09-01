from __future__ import annotations

import re

from bs4 import BeautifulSoup


class PortalError(Exception):
    """Falla recuperable de un portal: se registra en el log y se sigue con los demás."""


_TAGS_HTML = re.compile(r"<[^>]+>")
_ESPACIOS = re.compile(r"\s+")


def limpiar_html(html: str | None) -> str | None:
    if not html:
        return None
    try:
        texto = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    except Exception:  # noqa: BLE001
        texto = _TAGS_HTML.sub(" ", html)
    texto = _ESPACIOS.sub(" ", texto).strip()
    return texto or None
