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


# --- Relevancia por título -------------------------------------------------

from scraper.relevancia import es_relevante  # noqa: E402


def test_coordinador_de_logistica_no_es_deportivo():
    assert not es_relevante("Coordinador de Logística", "coordinador deportivo")
    assert es_relevante("Coordinador Deportivo", "coordinador deportivo")


def test_eventos_corporativos_no_son_deportivos():
    assert not es_relevante("Coordinadora de Eventos Corporativos", "eventos deportivos")


def test_operations_coordinator_generico_no_es_sports():
    assert not es_relevante("Operations Coordinator", "sports operations coordinator")


# --- Parser de Indeed -------------------------------------------------------

from scraper.portales.indeed import parsear  # noqa: E402

_INDEED_JSON = """<html><script>
window.mosaic.providerData["mosaic-provider-jobcards"]={"metaData":{"mosaicProviderJobCardsModel":{"results":[
{"jobkey":"abc123","displayTitle":"Coordinador Deportivo","company":"Club X",
 "formattedLocation":"Buenos Aires","remoteLocation":true,"pubDate":1790000000000,
 "snippet":"<ul><li>Organizar torneos</li></ul>","salarySnippet":{"text":"$ 900.000"}}
]}}};
window.mosaic.providerData["otro"]={};
</script></html>"""

_INDEED_HTML = """<html><ul><li>
<h2><a data-jk="def456"><span title="Sports Coordinator">Sports Coordinator</span></a></h2>
<span data-testid="company-name">Liga Y</span>
<div data-testid="text-location">Palermo, Buenos Aires</div>
</li></ul></html>"""


def test_indeed_lee_el_json_embebido():
    (av,) = parsear(_INDEED_JSON)
    assert av.portal_id == "abc123"
    assert av.titulo == "Coordinador Deportivo"
    assert av.modalidad == "remoto"
    assert av.url == "https://ar.indeed.com/viewjob?jk=abc123"
    assert av.descripcion == "Organizar torneos"
    assert av.salario == "$ 900.000"


def test_indeed_sin_json_lee_las_tarjetas():
    (av,) = parsear(_INDEED_HTML)
    assert av.portal_id == "def456"
    assert av.titulo == "Sports Coordinator"
    assert av.empresa == "Liga Y"
    assert av.ubicacion == "Palermo, Buenos Aires"
    assert av.url == "https://ar.indeed.com/viewjob?jk=def456"
