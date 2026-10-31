"""Tests de /churros."""

from crypto_tracker.alerts import formatear_churros
from crypto_tracker.churros import Churros


def test_cuantos():
    assert Churros(1_000).raciones == 250
    assert Churros(4).raciones == 1
    assert Churros(3.99).raciones == 0


def test_formatear():
    texto = formatear_churros(Churros(1_000), "eur")

    assert "🍫 <b>Tu cartera en chocolate con churros</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te da para <b>250 chocolates con churros</b>" in texto
    assert "Unos cada domingo, tienes para 4,8 años" in texto
    assert "<i>A unos €4 la taza con media docena</i>" in texto


def test_formatear_años_justos():
    # 52 domingos, sin "1,0 años"
    assert "tienes para 1 año\n" in formatear_churros(Churros(208), "eur")


def test_formatear_miles():
    assert "<b>2.500 chocolates" in formatear_churros(Churros(10_000), "eur")


def test_formatear_menos_de_un_año():
    texto = formatear_churros(Churros(40), "eur")

    assert "<b>10 chocolates con churros</b>" in texto
    assert "tienes para 10 semanas" in texto


def test_formatear_uno_y_ninguno():
    texto = formatear_churros(Churros(5), "eur")
    assert "<b>1 chocolate con churros</b>" in texto
    assert "tienes para 1 semana" in texto

    texto = formatear_churros(Churros(2), "eur")
    assert "No te da ni para un chocolate con churros 😅" in texto
    assert "domingo" not in texto
