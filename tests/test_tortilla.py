"""Tests de /tortilla."""

import pytest

from crypto_tracker.alerts import formatear_tortilla
from crypto_tracker.tortilla import Tortilla


def test_cuantos():
    t = Tortilla(3_000)

    assert t.pinchos == 1_000
    assert t.años == pytest.approx(2.740, abs=0.001)
    assert Tortilla(2.99).pinchos == 0


def test_formatear():
    texto = formatear_tortilla(Tortilla(3_000), "eur")

    assert "🥔 <b>Tu cartera en pinchos de tortilla</b>" in texto
    assert "Vale €3.000,00" in texto
    assert "Te da para <b>1.000 pinchos</b>" in texto
    assert "Uno cada mañana con el café, tienes para 2,7 años" in texto
    assert "<i>A unos €3 el pincho, en un bar de barrio</i>" in texto


def test_formatear_un_año_justo():
    # 365 pinchos, sin "1,0 años"
    assert "tienes para 1 año\n" in formatear_tortilla(Tortilla(1_095), "eur")


def test_formatear_menos_de_un_año():
    texto = formatear_tortilla(Tortilla(300), "eur")

    assert "<b>100 pinchos</b>" in texto
    assert "tienes para 100 días" in texto


def test_formatear_uno_y_ninguno():
    texto = formatear_tortilla(Tortilla(4), "eur")
    assert "<b>1 pincho</b>" in texto
    assert "tienes para 1 día" in texto

    texto = formatear_tortilla(Tortilla(2), "eur")
    assert "No te da ni para un pincho 😅" in texto
    assert "mañana" not in texto
