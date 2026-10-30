"""Tests de /metro."""

from crypto_tracker.alerts import formatear_metro
from crypto_tracker.metro import Metro


def test_cuantos():
    assert Metro(100).meses == 3
    assert Metro(30).meses == 1
    assert Metro(29).meses == 0


def test_formatear():
    texto = formatear_metro(Metro(1_000), "eur")

    assert "🚇 <b>Tu cartera en abonos de transporte</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te paga <b>33 meses</b>, más de 2 años" in texto
    assert "<i>A unos €30 el abono mensual</i>" in texto


def test_formatear_justo_un_año():
    assert "<b>12 meses</b>, justo 1 año" in formatear_metro(Metro(360), "eur")


def test_formatear_ni_uno():
    assert "No te paga ni un mes 😅" in formatear_metro(Metro(10), "eur")
