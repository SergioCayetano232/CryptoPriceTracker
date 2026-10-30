"""Tests de /ave."""

from crypto_tracker.alerts import formatear_ave
from crypto_tracker.ave import Ave


def test_cuantos():
    assert Ave(1_000).viajes == 12
    assert Ave(80).viajes == 1
    assert Ave(79).viajes == 0


def test_formatear():
    texto = formatear_ave(Ave(2_000), "eur")

    assert "🚄 <b>Tu cartera en AVE a Barcelona</b>" in texto
    assert "Vale €2.000,00" in texto
    assert "Te da para <b>25 viajes</b>" in texto
    assert "Un finde al mes, tienes escapadas para 2 años y pico" in texto
    assert "<i>A unos €80 ida y vuelta, desde Madrid</i>" in texto


def test_formatear_años_justos():
    assert "para 1 año\n" in formatear_ave(Ave(1_000), "eur")


def test_formatear_menos_de_un_año():
    texto = formatear_ave(Ave(400), "eur")

    assert "<b>5 viajes</b>" in texto
    assert "escapadas para 5 meses" in texto


def test_formatear_uno_y_ninguno():
    texto = formatear_ave(Ave(80), "eur")
    assert "<b>1 viaje</b>" in texto
    assert "escapadas para 1 mes" in texto
    texto = formatear_ave(Ave(50), "eur")
    assert "No te da ni para un viaje 😅" in texto
    assert "finde" not in texto
