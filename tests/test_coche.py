"""Tests de /coche."""

import pytest

from crypto_tracker.alerts import formatear_coche
from crypto_tracker.coche import Coche
from crypto_tracker.comandos import interpretar


def test_cuantos():
    assert Coche(60_000).enteros == 3
    assert Coche(19_999.99).enteros == 0
    assert Coche(5_000).parte == pytest.approx(25)


def test_falta():
    assert Coche(60_000).falta == 20_000
    assert Coche(45_000).falta == 15_000


def test_formatear():
    texto = formatear_coche(Coche(45_000), "eur")

    assert "🚗 <b>Tu cartera en coches</b>" in texto
    assert "Vale €45.000,00" in texto
    assert "Te da para <b>2 coches</b>" in texto
    assert "Para el siguiente te faltan €15.000,00" in texto
    assert "<i>A unos €20.000 cada uno, un utilitario nuevo</i>" in texto


def test_formatear_miles():
    assert "<b>1.000 coches</b>" in formatear_coche(Coche(20_000_000), "eur")


def test_formatear_uno():
    assert "Te da para <b>1 coche</b>" in formatear_coche(Coche(25_000), "eur")


def test_formatear_menos_de_uno():
    texto = formatear_coche(Coche(3_000), "eur")

    assert "Te da para el <b>15%</b> de uno" in texto
    assert "Para el primero te faltan €17.000,00" in texto


def test_comando():
    assert interpretar("/coche") == ("coche", "")
    assert interpretar("/coches") == ("coche", "")
