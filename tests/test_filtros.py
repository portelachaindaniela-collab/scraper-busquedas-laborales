"""Pruebas del filtro de descarte.  Correr con:  pytest"""
from __future__ import annotations

from scraper import config
from scraper.filtros import evaluar
from scraper.modelo import Aviso

FL = config.filtros()


def _aviso(titulo="Community Manager", descripcion="", ubicacion="Capital Federal", modalidad=None):
    return Aviso(
        portal="test", portal_id="1", titulo=titulo, empresa="X",
        ubicacion=ubicacion, modalidad=modalidad, salario=None,
        fecha_publicacion=None, url="http://x", descripcion=descripcion,
    )


def test_pasa_un_aviso_limpio():
    assert evaluar(_aviso(descripcion="Buscamos CM para redes sociales en CABA."), FL) == []


def test_descarta_ingles_avanzado():
    m = evaluar(_aviso(descripcion="Requisito: inglés avanzado (C1)."), FL)
    assert any("ingles_alto" in x for x in m)


def test_perdon_anula_descarte_de_ingles():
    assert evaluar(_aviso(descripcion="Inglés avanzado no excluyente, sólo deseable."), FL) == []


def test_descarta_google_ads():
    assert any("google_ads" in x for x in evaluar(_aviso(descripcion="Manejo de Google Ads requerido."), FL))


def test_descarta_ventas():
    assert any("ventas" in x for x in evaluar(_aviso(descripcion="Tareas de prospección y generación de leads."), FL))


def test_descarta_ubicacion_fuera_de_zona():
    m = evaluar(_aviso(ubicacion="Córdoba, Córdoba", descripcion="CM presencial."), FL)
    assert any("ubicacion" in x for x in m)


def test_remoto_salva_la_ubicacion():
    assert evaluar(_aviso(ubicacion="Córdoba", modalidad="remoto", descripcion="100% remoto."), FL) == []


def test_argentina_ambiguo_pasa():
    assert evaluar(_aviso(ubicacion="Argentina", descripcion="CM para redes."), FL) == []


def test_excluida_gana_a_argentina():
    m = evaluar(_aviso(ubicacion="San Francisco, Córdoba, Argentina", descripcion="CM."), FL)
    assert any("ubicacion" in x for x in m)


def test_gba_norte_pasa():
    assert evaluar(_aviso(ubicacion="San Isidro, Buenos Aires", descripcion="CM."), FL) == []


def test_camara():
    assert any("camara" in x for x in evaluar(_aviso(descripcion="Vas a presentar frente a cámara."), FL))
