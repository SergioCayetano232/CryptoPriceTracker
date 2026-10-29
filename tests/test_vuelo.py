"""Tests de /vuelo."""

import pytest

from crypto_tracker.alerts import formatear_vuelo
from crypto_tracker.vuelo import Vuelo


def test_cuantos():
    v = Vuelo(1_000)

    assert v.enteros == 1
    assert v.falta == pytest.approx(200)


def test_no_llega_a_uno():
    v = Vuelo(150)

    assert v.enteros == 0
    assert v.parte == pytest.approx(25)
    assert v.falta == pytest.approx(450)


def test_formatear():
    texto = formatear_vuelo(Vuelo(2_000), "eur")

    assert "✈️ <b>Tu cartera en vuelos a Nueva York</b>" in texto
    assert "Vale €2.000,00" in texto
    assert "Te da para <b>3 viajes</b>" in texto
    assert "Para el siguiente te faltan €400,00" in texto
    assert "<i>A unos €600 ida y vuelta, desde Madrid</i>" in texto


def test_formatear_uno_y_ninguno():
    assert "<b>1 viaje</b>" in formatear_vuelo(Vuelo(600), "eur")
    texto = formatear_vuelo(Vuelo(150), "eur")
    assert "Te da para el <b>25%</b> de uno" in texto
    assert "Para el primero te faltan €450,00" in texto
