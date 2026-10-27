"""Tests de /glosario."""

from crypto_tracker.alerts import formatear_glosario
from crypto_tracker.glosario import SINONIMOS, TERMINOS, buscar, parecido


def test_buscar():
    assert buscar("hodl") == "HODL"
    assert buscar(" FOMO ") == "FOMO"
    assert buscar("Halving") == "halving"
    assert buscar("whale") == "ballena"
    assert buscar("nft") is None


def test_los_sinonimos_llevan_a_algo():
    assert set(SINONIMOS.values()) <= set(TERMINOS)


def test_parecido():
    assert parecido("hodle") == "HODL"
    assert parecido("halvin") == "halving"
    assert parecido("pizza") is None


def test_formatear_lista():
    texto = formatear_glosario("")

    assert texto.startswith("📖 <b>Las palabras que sé</b>\nHODL, FOMO, FUD")
    assert "/glosario hodl" in texto


def test_formatear_uno():
    texto = formatear_glosario("dca")

    assert texto.startswith("📖 <b>DCA</b>\nMeter la misma cantidad")
    assert "/dca" in texto


def test_formatear_no_lo_sé():
    assert "¿Querías decir /glosario FOMO?" in formatear_glosario("fommo")
    texto = formatear_glosario("<b>nft</b>")
    assert "«&lt;b&gt;nft&lt;/b&gt;»" in texto
    assert "Con /glosario te salen las que sé" in texto
