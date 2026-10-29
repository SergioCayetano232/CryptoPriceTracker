"""Tests de /tesla."""

import pytest

from crypto_tracker.alerts import formatear_tesla
from crypto_tracker.tesla import Tesla


def test_cuantos():
    t = Tesla(90_000)

    assert t.enteros == 2
    assert t.falta == pytest.approx(30_000)


def test_no_llega_a_uno():
    t = Tesla(10_000)

    assert t.enteros == 0
    assert t.parte == pytest.approx(25)
    assert t.falta == pytest.approx(30_000)


def test_formatear():
    texto = formatear_tesla(Tesla(90_000), "eur")

    assert "🚗 <b>Tu cartera en Teslas</b>" in texto
    assert "Vale €90.000,00" in texto
    assert "Te da para <b>2 Teslas</b>" in texto
    assert "Para el siguiente te faltan €30.000,00" in texto
    assert "<i>A unos €40.000 cada uno, el Model 3</i>" in texto


def test_formatear_uno_y_ninguno():
    assert "<b>1 Tesla</b>" in formatear_tesla(Tesla(40_000), "eur")
    texto = formatear_tesla(Tesla(10_000), "eur")
    assert "Te da para el <b>25%</b> de uno" in texto
    assert "Para el primero te faltan €30.000,00" in texto
