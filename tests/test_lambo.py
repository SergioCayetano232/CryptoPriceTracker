"""Tests de /lambo."""

import pytest

from crypto_tracker.alerts import formatear_lambo
from crypto_tracker.lambo import Lambo


def test_sin_llegar_a_uno():
    lambo = Lambo(2_000)

    assert lambo.enteros == 0
    assert lambo.parte == pytest.approx(0.8)
    assert lambo.falta == 248_000


def test_varios():
    lambo = Lambo(600_000)

    assert lambo.enteros == 2
    assert lambo.falta == 150_000


def test_justo_uno():
    assert Lambo(250_000).enteros == 1
    assert Lambo(250_000).falta == 250_000


def test_formatear_sin_llegar():
    texto = formatear_lambo(Lambo(2_000), "usd")

    assert "Vale $2.000,00" in texto
    assert "Te da para el <b>0.80%</b> de uno" in texto
    assert "Para el primero te faltan $248.000,00" in texto
    assert "A unos $250.000 cada uno" in texto


def test_formatear_uno_y_varios():
    assert "<b>1 Lamborghini</b> 🎉" in formatear_lambo(Lambo(300_000), "eur")
    texto = formatear_lambo(Lambo(600_000), "eur")
    assert "<b>2 Lamborghinis</b> 🎉" in texto
    assert "Para el siguiente te faltan €150.000,00" in texto
