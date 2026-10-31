"""Tests de /peluqueria."""

from crypto_tracker.alerts import formatear_peluqueria
from crypto_tracker.peluqueria import Peluqueria


def test_cuantos():
    assert Peluqueria(1_000).cortes == 66
    assert Peluqueria(15).cortes == 1
    assert Peluqueria(14).cortes == 0


def test_formatear():
    texto = formatear_peluqueria(Peluqueria(1_000), "eur")

    assert "💈 <b>Tu cartera en cortes de pelo</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te da para <b>66 cortes</b>" in texto
    assert "Uno al mes, vas bien peinado <b>5 años</b> y pico" in texto
    assert "<i>A unos €15 el corte</i>" in texto


def test_formatear_años_justos():
    assert "<b>1 año</b>\n" in formatear_peluqueria(Peluqueria(180), "eur")


def test_formatear_menos_de_un_año():
    texto = formatear_peluqueria(Peluqueria(100), "eur")

    assert "<b>6 cortes</b>" in texto
    assert "vas bien peinado <b>6 meses</b>" in texto


def test_formatear_uno_y_ninguno():
    texto = formatear_peluqueria(Peluqueria(15), "eur")
    assert "<b>1 corte</b>" in texto
    assert "<b>1 mes</b>" in texto

    texto = formatear_peluqueria(Peluqueria(10), "eur")
    assert "No te da ni para un corte 😅" in texto
    assert "peinado" not in texto
