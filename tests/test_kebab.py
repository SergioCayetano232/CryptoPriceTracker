"""Tests de /kebab."""

import pytest

from crypto_tracker.alerts import formatear_kebab
from crypto_tracker.kebab import Kebab


def test_cuantos():
    k = Kebab(1_000)

    assert k.kebabs == 166
    assert k.años == pytest.approx(3.192, abs=0.001)


def test_no_llega_a_uno():
    assert Kebab(5).kebabs == 0


def test_formatear():
    texto = formatear_kebab(Kebab(1_000), "eur")

    assert "🥙 <b>Tu cartera en kebabs</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te da para <b>166 kebabs</b>" in texto
    assert "Uno cada viernes, cenas 3,2 años" in texto
    assert "<i>A unos €6 el kebab</i>" in texto


def test_formatear_menos_de_un_año():
    texto = formatear_kebab(Kebab(60), "eur")

    assert "<b>10 kebabs</b>" in texto
    assert "cenas 10 viernes" in texto


def test_formatear_un_año_justo():
    # 52 kebabs no puede salir como "1,0 años"
    texto = formatear_kebab(Kebab(318), "eur")

    assert "cenas 1 año" in texto


def test_formatear_uno_y_ninguno():
    texto = formatear_kebab(Kebab(6), "eur")
    assert "<b>1 kebab</b>" in texto
    assert "cenas 1 viernes" in texto
    texto = formatear_kebab(Kebab(5), "eur")
    assert "No te da ni para un kebab 😅" in texto
    assert "viernes" not in texto
