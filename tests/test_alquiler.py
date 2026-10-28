"""Tests de /alquiler."""

from crypto_tracker.alerts import formatear_alquiler
from crypto_tracker.alquiler import Alquiler


def test_cuantos():
    assert Alquiler(4_000).meses == 3
    assert Alquiler(500).meses == 0
    assert Alquiler(550).dias == 15


def test_formatear():
    texto = formatear_alquiler(Alquiler(4_000), "eur")

    assert "🏠 <b>Tu cartera en meses de alquiler</b>" in texto
    assert "Vale €4.000,00" in texto
    assert "Te paga <b>3 meses</b>" in texto
    assert "<i>A unos €1.100 al mes, un piso normal en España</i>" in texto


def test_formatear_un_mes_y_ninguno():
    assert "<b>1 mes</b>" in formatear_alquiler(Alquiler(1_100), "eur")
    texto = formatear_alquiler(Alquiler(550), "eur")
    assert "No llega a un mes: te paga <b>15 días</b>" in texto


def test_formatear_años():
    def texto(valor):
        return formatear_alquiler(Alquiler(valor), "eur")

    assert "<b>30 meses</b>, más de 2 años" in texto(33_000)
    assert "<b>24 meses</b>, justo 2 años" in texto(26_400)
    assert "<b>13 meses</b>, más de 1 año" in texto(14_300)
