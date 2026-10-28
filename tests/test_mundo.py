"""Tests de /mundo."""

from crypto_tracker.alerts import formatear_mundo
from crypto_tracker.mundo import Mundo


def test_cuentas():
    m = Mundo(83_000)

    assert m.sats == 253_012
    assert round(m.valor, 2) == 210.0


def test_formatear():
    texto = formatear_mundo(Mundo(83_000), "eur")

    assert "🌍 <b>Si se repartieran todos los bitcoin</b>" in texto
    assert "8.300 millones de personas" in texto
    assert "<b>253.012 sats</b>" in texto
    assert "unos <b>€210,00</b>" in texto


def test_formatear_en_dolares():
    assert "unos <b>$210,00</b>" in formatear_mundo(Mundo(83_000), "usd")
