"""Tests de /jamon."""

import pytest

from crypto_tracker.alerts import formatear_jamon
from crypto_tracker.comandos import interpretar
from crypto_tracker.jamon import Jamon


def test_cuantos():
    assert Jamon(1500).enteros == 3
    assert Jamon(499.99).enteros == 0
    assert Jamon(100).parte == pytest.approx(20)


def test_falta():
    assert Jamon(1500).falta == 500
    assert Jamon(1200).falta == 300


def test_formatear():
    texto = formatear_jamon(Jamon(1200), "eur")

    assert "🍖 <b>Tu cartera en jamones</b>" in texto
    assert "Vale €1.200,00" in texto
    assert "Te da para <b>2 jamones</b>" in texto
    assert "Para el siguiente te faltan €300,00" in texto
    assert "<i>A unos €500 la pata de bellota 100% ibérica</i>" in texto


def test_formatear_miles():
    assert "<b>1.000 jamones</b>" in formatear_jamon(Jamon(500_000), "eur")


def test_formatear_uno():
    assert "Te da para <b>1 jamón</b>" in formatear_jamon(Jamon(700), "eur")


def test_formatear_menos_de_uno():
    texto = formatear_jamon(Jamon(60), "eur")

    assert "Te da para el <b>12%</b> de uno" in texto
    assert "Para el primero te faltan €440,00" in texto


def test_comando():
    assert interpretar("/jamon") == ("jamon", "")
    assert interpretar("/jamón") == ("jamon", "")
    assert interpretar("/jamones") == ("jamon", "")
