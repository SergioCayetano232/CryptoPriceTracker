"""Tests de /cine."""

import pytest

from crypto_tracker.alerts import formatear_cine
from crypto_tracker.cine import Cine


def test_cuantas():
    c = Cine(1_000)

    assert c.entradas == 111
    assert c.años == pytest.approx(2.135, abs=0.001)


def test_no_llega_a_una():
    assert Cine(8).entradas == 0


def test_formatear():
    texto = formatear_cine(Cine(1_000), "eur")

    assert "🎬 <b>Tu cartera en cine</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te da para <b>111 entradas</b>" in texto
    assert "Una peli a la semana, tienes para 2,1 años" in texto
    assert "<i>A unos €9 la entrada</i>" in texto


def test_formatear_menos_de_un_año():
    texto = formatear_cine(Cine(90), "eur")

    assert "<b>10 entradas</b>" in texto
    assert "tienes para 10 semanas" in texto


def test_formatear_una_y_ninguna():
    texto = formatear_cine(Cine(9), "eur")
    assert "<b>1 entrada</b>" in texto
    assert "tienes para 1 semana" in texto
    texto = formatear_cine(Cine(5), "eur")
    assert "No te da ni para una entrada 😅" in texto
    assert "a la semana" not in texto
