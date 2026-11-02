"""Tests de /boda."""

import pytest

from crypto_tracker.alerts import formatear_boda
from crypto_tracker.boda import Boda
from crypto_tracker.comandos import interpretar


def test_cuantas():
    assert Boda(75_000).enteros == 3
    assert Boda(24_999.99).enteros == 0
    assert Boda(5_000).parte == pytest.approx(20)


def test_falta():
    assert Boda(75_000).falta == 25_000
    assert Boda(60_000).falta == 15_000


def test_formatear():
    texto = formatear_boda(Boda(60_000), "eur")

    assert "💍 <b>Tu cartera en bodas</b>" in texto
    assert "Vale €60.000,00" in texto
    assert "Te da para <b>2 bodas</b>" in texto
    assert "Para la siguiente te faltan €15.000,00" in texto
    assert "<i>A unos €25.000 cada una, con cien invitados</i>" in texto


def test_formatear_miles():
    assert "<b>1.000 bodas</b>" in formatear_boda(Boda(25_000_000), "eur")


def test_formatear_una():
    assert "Te da para <b>1 boda</b>" in formatear_boda(Boda(30_000), "eur")


def test_formatear_menos_de_una():
    texto = formatear_boda(Boda(3_000), "eur")

    assert "Te da para el <b>12%</b> de una" in texto
    assert "Para la primera te faltan €22.000,00" in texto


def test_comando():
    assert interpretar("/boda") == ("boda", "")
    assert interpretar("/bodas") == ("boda", "")
    assert interpretar("/casarse") == ("boda", "")
