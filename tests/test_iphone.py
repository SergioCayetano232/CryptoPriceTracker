"""Tests de /iphone."""

import pytest

from crypto_tracker.alerts import formatear_iphone
from crypto_tracker.iphone import Iphone


def test_cuantos():
    i = Iphone(4_000)

    assert i.enteros == 2
    assert i.falta == pytest.approx(500)


def test_no_llega_a_uno():
    i = Iphone(600)

    assert i.enteros == 0
    assert i.parte == pytest.approx(40)
    assert i.falta == pytest.approx(900)


def test_formatear():
    texto = formatear_iphone(Iphone(4_000), "eur")

    assert "📱 <b>Tu cartera en iPhones</b>" in texto
    assert "Vale €4.000,00" in texto
    assert "Te da para <b>2 iPhones</b>" in texto
    assert "Para el siguiente te faltan €500,00" in texto
    assert "<i>A unos €1.500 cada uno, el Pro</i>" in texto


def test_formatear_uno_y_ninguno():
    assert "<b>1 iPhone</b>" in formatear_iphone(Iphone(1_500), "eur")
    texto = formatear_iphone(Iphone(600), "eur")
    assert "Te da para el <b>40%</b> de uno" in texto
    assert "Para el primero te faltan €900,00" in texto
