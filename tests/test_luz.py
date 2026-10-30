"""Tests de /luz."""

from crypto_tracker.alerts import formatear_luz
from crypto_tracker.luz import Luz


def test_cuantos():
    assert Luz(200).meses == 3
    assert Luz(60).meses == 1
    assert Luz(59).meses == 0


def test_formatear():
    texto = formatear_luz(Luz(1_000), "eur")

    assert "💡 <b>Tu cartera en facturas de la luz</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te paga <b>16 meses</b>, más de 1 año" in texto
    assert "<i>A unos €60 la factura del mes</i>" in texto


def test_formatear_justo_un_año():
    assert "<b>12 meses</b>, justo 1 año" in formatear_luz(Luz(720), "eur")


def test_formatear_ni_uno():
    assert "No te paga ni un mes 😅" in formatear_luz(Luz(30), "eur")
