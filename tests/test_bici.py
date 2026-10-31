"""Tests de /bici."""

import pytest

from crypto_tracker.alerts import formatear_bici
from crypto_tracker.bici import Bici


def test_cuantas():
    assert Bici(2_000).enteras == 2
    assert Bici(800).enteras == 1
    assert Bici(799).enteras == 0


def test_falta():
    assert Bici(2_000).falta == pytest.approx(400)
    assert Bici(800).falta == pytest.approx(800)


def test_formatear():
    texto = formatear_bici(Bici(2_000), "eur")

    assert "🚴 <b>Tu cartera en bicis</b>" in texto
    assert "Vale €2.000,00" in texto
    assert "Te da para <b>2 bicis de carretera</b>" in texto
    assert "Para la siguiente te faltan €400,00" in texto
    assert "<i>A unos €800 cada una, de aluminio para empezar</i>" in texto


def test_formatear_una_y_miles():
    assert "<b>1 bici de carretera</b>" in formatear_bici(Bici(900), "eur")
    assert "<b>1.000 bicis" in formatear_bici(Bici(800_000), "eur")


def test_formatear_menos_de_una():
    texto = formatear_bici(Bici(200), "eur")

    assert "Te da para el <b>25%</b> de una" in texto
    assert "Para la primera te faltan €600,00" in texto
