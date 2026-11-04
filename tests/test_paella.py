"""Tests de /paella."""

import pytest

from crypto_tracker.alerts import formatear_paella
from crypto_tracker.comandos import interpretar
from crypto_tracker.paella import Paella


def test_cuantos():
    assert Paella(180).enteros == 3
    assert Paella(59.99).enteros == 0
    assert Paella(15).parte == pytest.approx(25)


def test_falta():
    assert Paella(180).falta == 60
    assert Paella(150).falta == 30


def test_formatear():
    texto = formatear_paella(Paella(150), "eur")

    assert "🥘 <b>Tu cartera en paellas</b>" in texto
    assert "Vale €150,00" in texto
    assert "Te da para <b>2 paellas</b>" in texto
    assert "Para la siguiente te faltan €30,00" in texto
    assert "<i>A unos €60 la de cuatro en un restaurante</i>" in texto


def test_formatear_miles():
    assert "<b>1.000 paellas</b>" in formatear_paella(Paella(60_000), "eur")


def test_formatear_una():
    assert "Te da para <b>1 paella</b>" in formatear_paella(Paella(70), "eur")


def test_formatear_menos_de_una():
    texto = formatear_paella(Paella(15), "eur")

    assert "Te da para el <b>25%</b> de una" in texto
    assert "Para la primera te faltan €45,00" in texto


def test_comando():
    assert interpretar("/paella") == ("paella", "")
    assert interpretar("/paellas") == ("paella", "")
