"""Tests de /netflix."""

from crypto_tracker.alerts import formatear_netflix
from crypto_tracker.netflix import Netflix


def test_cuantos():
    assert Netflix(100).meses == 7
    assert Netflix(13.99).meses == 1
    assert Netflix(10).meses == 0


def test_formatear():
    texto = formatear_netflix(Netflix(1_520), "eur")

    assert "🍿 <b>Tu cartera en Netflix</b>" in texto
    assert "Vale €1.520,00" in texto
    assert "Te paga <b>108 meses</b>, justo 9 años" in texto
    assert "<i>A €13,99 al mes, el plan Estándar</i>" in texto


def test_formatear_mucho():
    assert "<b>7.147 meses</b>, más de 595 años" in formatear_netflix(
        Netflix(100_000), "eur"
    )


def test_formatear_ni_uno():
    texto = formatear_netflix(Netflix(10), "eur")
    assert "No te paga ni un mes 😅" in texto
