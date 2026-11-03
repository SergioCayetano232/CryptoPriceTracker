"""Tests de /rolex."""

import pytest

from crypto_tracker.alerts import formatear_rolex
from crypto_tracker.comandos import interpretar
from crypto_tracker.rolex import Rolex


def test_cuantos():
    assert Rolex(30_000).enteros == 3
    assert Rolex(9_999.99).enteros == 0
    assert Rolex(2_000).parte == pytest.approx(20)


def test_falta():
    assert Rolex(30_000).falta == 10_000
    assert Rolex(24_000).falta == 6_000


def test_formatear():
    texto = formatear_rolex(Rolex(24_000), "eur")

    assert "⌚ <b>Tu cartera en Rolex</b>" in texto
    assert "Vale €24.000,00" in texto
    assert "Te da para <b>2 Rolex</b>" in texto
    assert "Para el siguiente te faltan €6.000,00" in texto
    assert "<i>A unos €10.000 un Submariner nuevo</i>" in texto


def test_formatear_miles():
    assert "<b>1.000 Rolex</b>" in formatear_rolex(Rolex(10_000_000), "eur")


def test_formatear_uno():
    assert "Te da para <b>1 Rolex</b>" in formatear_rolex(Rolex(15_000), "eur")


def test_formatear_menos_de_uno():
    texto = formatear_rolex(Rolex(1_200), "eur")

    assert "Te da para el <b>12%</b> de uno" in texto
    assert "Para el primero te faltan €8.800,00" in texto


def test_comando():
    assert interpretar("/rolex") == ("rolex", "")
    assert interpretar("/reloj") == ("rolex", "")
