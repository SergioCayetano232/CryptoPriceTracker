"""Tests de /macbook."""

import pytest

from crypto_tracker.alerts import formatear_macbook
from crypto_tracker.macbook import Macbook


def test_cuantos():
    assert Macbook(3_000).enteros == 2
    assert Macbook(1_300).enteros == 1
    assert Macbook(1_299).enteros == 0


def test_falta():
    assert Macbook(3_000).falta == pytest.approx(900)
    assert Macbook(1_300).falta == pytest.approx(1_300)


def test_formatear():
    texto = formatear_macbook(Macbook(3_000), "eur")

    assert "💻 <b>Tu cartera en MacBooks</b>" in texto
    assert "Vale €3.000,00" in texto
    assert "Te da para <b>2 MacBook Air</b>" in texto
    assert "Para el siguiente te faltan €900,00" in texto
    assert '<i>A unos €1.300 cada uno, el Air de 13"</i>' in texto


def test_formatear_miles():
    assert "<b>1.000 MacBook Air</b>" in formatear_macbook(Macbook(1_300_000), "eur")


def test_formatear_menos_de_uno():
    texto = formatear_macbook(Macbook(650), "eur")

    assert "Te da para el <b>50%</b> de uno" in texto
    assert "Para el primero te faltan €650,00" in texto
