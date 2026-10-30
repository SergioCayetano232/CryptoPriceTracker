"""Tests de /airpods."""

import pytest

from crypto_tracker.airpods import Airpods
from crypto_tracker.alerts import formatear_airpods


def test_cuantos():
    a = Airpods(1_000)

    assert a.enteros == 4
    assert a.falta == pytest.approx(250)


def test_no_llega_a_unos():
    a = Airpods(125)

    assert a.enteros == 0
    assert a.parte == pytest.approx(50)
    assert a.falta == pytest.approx(125)


def test_formatear():
    texto = formatear_airpods(Airpods(1_100), "eur")

    assert "🎧 <b>Tu cartera en AirPods Pro</b>" in texto
    assert "Vale €1.100,00" in texto
    assert "Te da para <b>4 AirPods Pro</b>" in texto
    assert "Para los siguientes te faltan €150,00" in texto
    assert "<i>A unos €250 cada uno</i>" in texto


def test_formatear_ninguno():
    texto = formatear_airpods(Airpods(125), "eur")
    assert "Te da para el <b>50%</b> de unos" in texto
    assert "Para los primeros te faltan €125,00" in texto
