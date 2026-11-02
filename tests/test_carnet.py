"""Tests de /carnet."""

import pytest

from crypto_tracker.alerts import formatear_carnet
from crypto_tracker.carnet import Carnet
from crypto_tracker.comandos import interpretar


def test_cuantos():
    assert Carnet(2_400).enteros == 3
    assert Carnet(799.99).enteros == 0
    assert Carnet(200).parte == pytest.approx(25)


def test_falta():
    assert Carnet(2_400).falta == 800
    assert Carnet(3_000).falta == 200


def test_formatear():
    texto = formatear_carnet(Carnet(3_000), "eur")

    assert "🚦 <b>Tu cartera en carnets de conducir</b>" in texto
    assert "Vale €3.000,00" in texto
    assert "Te da para <b>3 carnets</b>" in texto
    assert "Para el siguiente te faltan €200,00" in texto
    assert "<i>A unos €800 cada uno, aprobando a la primera</i>" in texto


def test_formatear_miles():
    assert "<b>1.000 carnets</b>" in formatear_carnet(Carnet(800_000), "eur")


def test_formatear_uno():
    assert "Te da para <b>1 carnet</b>" in formatear_carnet(Carnet(900), "eur")


def test_formatear_menos_de_uno():
    texto = formatear_carnet(Carnet(200), "eur")

    assert "Te da para el <b>25%</b> de uno" in texto
    assert "Para el primero te faltan €600,00" in texto


def test_comando():
    assert interpretar("/carnet") == ("carnet", "")
    assert interpretar("/carne") == ("carnet", "")
    assert interpretar("/autoescuela") == ("carnet", "")
