"""Tests de /switch."""

import pytest

from crypto_tracker.alerts import formatear_switch
from crypto_tracker.switch import Switch


def test_cuantas():
    s = Switch(1_000)

    assert s.enteros == 2
    assert s.falta == pytest.approx(410)


def test_no_llega_a_una():
    s = Switch(235)

    assert s.enteros == 0
    assert s.parte == pytest.approx(50)
    assert s.falta == pytest.approx(235)


def test_formatear():
    texto = formatear_switch(Switch(1_000), "eur")

    assert "🕹️ <b>Tu cartera en Switch 2</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te da para <b>2 Switch 2</b>" in texto
    assert "Para la siguiente te faltan €410,00" in texto
    assert "<i>A unos €470 cada una, sin juego</i>" in texto


def test_formatear_ninguna():
    texto = formatear_switch(Switch(235), "eur")
    assert "Te da para el <b>50%</b> de una" in texto
    assert "Para la primera te faltan €235,00" in texto
