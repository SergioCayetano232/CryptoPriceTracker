"""Tests de /ps5."""

import pytest

from crypto_tracker.alerts import formatear_ps5
from crypto_tracker.ps5 import Ps5


def test_cuantas():
    p = Ps5(2_000)

    assert p.enteros == 2
    assert p.falta == pytest.approx(400)


def test_no_llega_a_una():
    p = Ps5(200)

    assert p.enteros == 0
    assert p.parte == pytest.approx(25)
    assert p.falta == pytest.approx(600)


def test_formatear():
    texto = formatear_ps5(Ps5(2_000), "eur")

    assert "🎮 <b>Tu cartera en PS5</b>" in texto
    assert "Vale €2.000,00" in texto
    assert "Te da para <b>2 PS5</b>" in texto
    assert "Para la siguiente te faltan €400,00" in texto
    assert "<i>A unos €800 cada una, la Pro</i>" in texto


def test_formatear_una_y_ninguna():
    assert "<b>1 PS5</b>" in formatear_ps5(Ps5(800), "eur")
    texto = formatear_ps5(Ps5(200), "eur")
    assert "Te da para el <b>25%</b> de una" in texto
    assert "Para la primera te faltan €600,00" in texto
