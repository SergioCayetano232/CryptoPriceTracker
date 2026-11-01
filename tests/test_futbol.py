"""Tests de /futbol."""

import pytest

from crypto_tracker.alerts import formatear_futbol
from crypto_tracker.futbol import Futbol


def test_cuantos():
    f = Futbol(3_000)

    assert f.entradas == 50
    assert f.temporadas == pytest.approx(2.632, abs=0.001)
    assert Futbol(59.99).entradas == 0


def test_formatear():
    texto = formatear_futbol(Futbol(3_000), "eur")

    assert "⚽ <b>Tu cartera en entradas de fútbol</b>" in texto
    assert "Vale €3.000,00" in texto
    assert "Te da para <b>50 entradas</b>" in texto
    assert "Yendo a todos los partidos en casa, tienes para 2,6 temporadas" in texto
    assert "<i>A unos €60 la entrada, en un partido de liga</i>" in texto


def test_formatear_una_temporada_justa():
    # 19 entradas, sin "1,0 temporadas"
    texto = formatear_futbol(Futbol(1_140), "eur")

    assert "tienes para 1 temporada\n" in texto


def test_formatear_miles():
    assert "<b>1.666 entradas</b>" in formatear_futbol(Futbol(100_000), "eur")


def test_formatear_menos_de_una_temporada():
    texto = formatear_futbol(Futbol(600), "eur")

    assert "<b>10 entradas</b>" in texto
    assert "tienes para 10 partidos" in texto


def test_formatear_una_y_ninguna():
    texto = formatear_futbol(Futbol(60), "eur")
    assert "<b>1 entrada</b>" in texto
    assert "tienes para 1 partido" in texto

    texto = formatear_futbol(Futbol(30), "eur")
    assert "No te da ni para una entrada 😅" in texto
    assert "en casa" not in texto
