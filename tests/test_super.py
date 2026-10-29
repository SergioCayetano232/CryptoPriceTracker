"""Tests de /super."""

import pytest

from crypto_tracker.alerts import formatear_super
from crypto_tracker.supermercado import Super


def test_cuantos():
    s = Super(10_000)

    assert s.carros == 100
    assert s.años == pytest.approx(1.923, abs=0.001)


def test_no_llega_a_uno():
    assert Super(99).carros == 0


def test_formatear():
    texto = formatear_super(Super(10_000), "eur")

    assert "🛒 <b>Tu cartera en carros de la compra</b>" in texto
    assert "Vale €10.000,00" in texto
    assert "Te da para <b>100 carros</b>" in texto
    assert "Uno a la semana, comes 1,9 años" in texto
    assert "<i>A unos €100 el carro</i>" in texto


def test_formatear_años_justos():
    assert "comes 1 año" in formatear_super(Super(5_400), "eur")
    assert "comes 2 años" in formatear_super(Super(10_400), "eur")


def test_formatear_menos_de_un_año():
    texto = formatear_super(Super(2_000), "eur")

    assert "<b>20 carros</b>" in texto
    assert "comes 20 semanas" in texto


def test_formatear_uno_y_ninguno():
    texto = formatear_super(Super(100), "eur")
    assert "<b>1 carro</b>" in texto
    assert "comes 1 semana" in texto
    texto = formatear_super(Super(50), "eur")
    assert "No te da ni para un carro 😅" in texto
    assert "a la semana" not in texto
