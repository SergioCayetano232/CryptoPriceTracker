"""Tests de /cafe."""

import pytest

from crypto_tracker.alerts import formatear_cafe
from crypto_tracker.cafe import Cafe


def test_cuantos():
    cafe = Cafe(2_000)

    assert cafe.cuantos == 1333
    assert cafe.años == pytest.approx(3.652, abs=0.001)


def test_no_llega_a_uno():
    assert Cafe(1.2).cuantos == 0


def test_formatear():
    texto = formatear_cafe(Cafe(2_000), "eur")

    assert "☕ <b>Tu cartera en cafés</b>" in texto
    assert "Vale €2.000,00" in texto
    assert "Te da para <b>1.333 cafés</b>" in texto
    assert "Uno al día, tienes para 3,7 años" in texto
    assert "<i>A €1,50 cada uno</i>" in texto


def test_formatear_menos_de_un_año():
    texto = formatear_cafe(Cafe(150), "usd")

    assert "<b>100 cafés</b>" in texto
    assert "Uno al día, tienes para 100 días" in texto


def test_formatear_uno_y_ninguno():
    assert "<b>1 café</b>" in formatear_cafe(Cafe(2), "eur")
    assert "Uno al día, tienes para 1 día" in formatear_cafe(Cafe(2), "eur")
    texto = formatear_cafe(Cafe(1), "eur")
    assert "No te da ni para un café" in texto
    assert "Uno al día" not in texto
