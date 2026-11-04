"""Tests de /croquetas."""

import pytest

from crypto_tracker.alerts import formatear_croquetas
from crypto_tracker.comandos import interpretar
from crypto_tracker.croquetas import Croquetas


def test_cuantos():
    assert Croquetas(30).enteros == 3
    assert Croquetas(9.99).enteros == 0
    assert Croquetas(2.5).parte == pytest.approx(25)


def test_falta():
    assert Croquetas(30).falta == 10
    assert Croquetas(26).falta == 4


def test_formatear():
    texto = formatear_croquetas(Croquetas(26), "eur")

    assert "🧆 <b>Tu cartera en croquetas</b>" in texto
    assert "Vale €26,00" in texto
    assert "Te da para <b>2 raciones</b>" in texto
    assert "Para la siguiente te faltan €4,00" in texto
    assert "<i>A unos €10 la ración de ocho caseras</i>" in texto


def test_formatear_miles():
    assert "<b>1.000 raciones</b>" in formatear_croquetas(Croquetas(10_000), "eur")


def test_formatear_una():
    assert "Te da para <b>1 ración</b>" in formatear_croquetas(Croquetas(15), "eur")


def test_formatear_menos_de_una():
    texto = formatear_croquetas(Croquetas(2.5), "eur")

    assert "Te da para el <b>25%</b> de una" in texto
    assert "Para la primera te faltan €7,50" in texto


def test_comando():
    assert interpretar("/croquetas") == ("croquetas", "")
    assert interpretar("/croqueta") == ("croquetas", "")
