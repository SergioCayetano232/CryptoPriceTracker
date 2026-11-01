"""Tests de /sofa."""

import pytest

from crypto_tracker.alerts import formatear_sofa
from crypto_tracker.sofa import Sofa


def test_cuantos():
    assert Sofa(3_000).enteros == 6
    assert Sofa(499.99).enteros == 0
    assert Sofa(250).parte == pytest.approx(50)


def test_falta():
    assert Sofa(3_000).falta == 500
    assert Sofa(3_200).falta == 300


def test_formatear():
    texto = formatear_sofa(Sofa(3_200), "eur")

    assert "🛋️ <b>Tu cartera en sofás</b>" in texto
    assert "Vale €3.200,00" in texto
    assert "Te da para <b>6 sofás</b>" in texto
    assert "Para el siguiente te faltan €300,00" in texto
    assert "<i>A unos €500 cada uno, de tres plazas de IKEA</i>" in texto


def test_formatear_miles():
    assert "<b>2.000 sofás</b>" in formatear_sofa(Sofa(1_000_000), "eur")


def test_formatear_uno():
    assert "Te da para <b>1 sofá</b>" in formatear_sofa(Sofa(600), "eur")


def test_formatear_menos_de_uno():
    texto = formatear_sofa(Sofa(150), "eur")

    assert "Te da para el <b>30%</b> de uno" in texto
    assert "Para el primero te faltan €350,00" in texto
