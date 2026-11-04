"""Tests de /aceite."""

import pytest

from crypto_tracker.aceite import Aceite
from crypto_tracker.alerts import formatear_aceite
from crypto_tracker.comandos import interpretar


def test_cuantos():
    assert Aceite(80).enteros == 10
    assert Aceite(7.99).enteros == 0
    assert Aceite(2).parte == pytest.approx(25)


def test_falta():
    assert Aceite(80).falta == 8
    assert Aceite(75).falta == 5


def test_formatear():
    texto = formatear_aceite(Aceite(75), "eur")

    assert "🫒 <b>Tu cartera en aceite de oliva</b>" in texto
    assert "Vale €75,00" in texto
    assert "Te da para <b>9 litros</b>" in texto
    assert "Para el siguiente te faltan €5,00" in texto
    assert "<i>A unos €8 el litro de virgen extra</i>" in texto


def test_formatear_miles():
    assert "<b>1.000 litros</b>" in formatear_aceite(Aceite(8000), "eur")


def test_formatear_uno():
    assert "Te da para <b>1 litro</b>" in formatear_aceite(Aceite(10), "eur")


def test_formatear_menos_de_uno():
    texto = formatear_aceite(Aceite(2), "eur")

    assert "Te da para el <b>25%</b> de uno" in texto
    assert "Para el primero te faltan €6,00" in texto


def test_comando():
    assert interpretar("/aceite") == ("aceite", "")
    assert interpretar("/aove") == ("aceite", "")
    assert interpretar("/oliva") == ("aceite", "")
