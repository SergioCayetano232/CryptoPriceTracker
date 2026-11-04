"""Tests de /pan."""

import pytest

from crypto_tracker.alerts import formatear_pan
from crypto_tracker.comandos import interpretar
from crypto_tracker.pan import Pan


def test_cuantos():
    assert Pan(12).enteros == 10
    assert Pan(1.19).enteros == 0
    assert Pan(0.3).parte == pytest.approx(25)


def test_sin_fallos_de_decimales():
    assert Pan(3.6).enteros == 3
    assert Pan(3.6).falta == pytest.approx(1.2)


def test_falta():
    assert Pan(12).falta == pytest.approx(1.2)
    assert Pan(11).falta == pytest.approx(1)


def test_formatear():
    texto = formatear_pan(Pan(11), "eur")

    assert "🥖 <b>Tu cartera en barras de pan</b>" in texto
    assert "Vale €11,00" in texto
    assert "Te da para <b>9 barras</b>" in texto
    assert "Para la siguiente te faltan €1,00" in texto
    assert "<i>A unos €1,20 la barra en la panadería</i>" in texto


def test_formatear_miles():
    assert "<b>1.000 barras</b>" in formatear_pan(Pan(1200), "eur")


def test_formatear_una():
    assert "Te da para <b>1 barra</b>" in formatear_pan(Pan(2), "eur")


def test_formatear_menos_de_una():
    texto = formatear_pan(Pan(0.3), "eur")

    assert "Te da para el <b>25%</b> de una" in texto
    assert "Para la primera te faltan €0,90\n" in texto


def test_comando():
    assert interpretar("/pan") == ("pan", "")
    assert interpretar("/barras") == ("pan", "")
