"""Tests de /gimnasio."""

from crypto_tracker.alerts import formatear_gimnasio
from crypto_tracker.gimnasio import Gimnasio


def test_cuantos():
    assert Gimnasio(100).meses == 2
    assert Gimnasio(40).meses == 1
    assert Gimnasio(39).meses == 0


def test_formatear():
    texto = formatear_gimnasio(Gimnasio(1_000), "eur")

    assert "🏋️ <b>Tu cartera en gimnasio</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te paga <b>25 meses</b>, más de 2 años" in texto
    assert "<i>A unos €40 al mes</i>" in texto


def test_formatear_ni_uno():
    assert "No te paga ni un mes 😅" in formatear_gimnasio(Gimnasio(10), "eur")
