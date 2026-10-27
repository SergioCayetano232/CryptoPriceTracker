"""Tests de /gasolina."""

from crypto_tracker.alerts import formatear_gasolina
from crypto_tracker.gasolina import Gasolina


def test_litros_y_depositos():
    g = Gasolina(2_000)

    assert g.litros == 1111
    assert g.depositos == 22


def test_no_llega_a_un_deposito():
    assert Gasolina(80).depositos == 0


def test_formatear():
    texto = formatear_gasolina(Gasolina(2_000), "eur")

    assert "⛽ <b>Tu cartera en gasolina</b>" in texto
    assert "Vale €2.000,00" in texto
    assert "Te da para <b>1.111 litros</b>" in texto
    assert "Son 22 depósitos de 50 litros" in texto
    assert "<i>A unos €1,80 el litro</i>" in texto


def test_formatear_sin_deposito():
    texto = formatear_gasolina(Gasolina(80), "usd")

    assert "<b>44 litros</b>" in texto
    assert "depósito" not in texto


def test_formatear_uno_y_ninguno():
    assert "<b>1 litro</b>" in formatear_gasolina(Gasolina(2), "eur")
    assert "Son 1 depósito de" in formatear_gasolina(Gasolina(91), "eur")
    assert "No te da ni para un litro" in formatear_gasolina(Gasolina(1), "eur")
