"""Carga de los archivos de configuración editables (config/*.yml)."""
from __future__ import annotations

import pathlib

import yaml

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CONFIG_DIR = RAIZ / "config"


def _cargar(nombre: str) -> dict:
    with open(CONFIG_DIR / nombre, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def busquedas() -> dict:
    return _cargar("busquedas.yml")


def filtros() -> dict:
    return _cargar("filtros.yml")
