"""Tests de /menu."""

from crypto_tracker.alerts import formatear_menu
from crypto_tracker.menu import Menu


def test_cuantos():
    assert Menu(1_000).menus == 76
    assert Menu(13).menus == 1
    assert Menu(12).menus == 0


def test_semanas():
    assert Menu(1_000).semanas == 15
    assert Menu(64).semanas == 0
    assert Menu(65).semanas == 1


def test_formatear():
    texto = formatear_menu(Menu(1_000), "eur")

    assert "🍽 <b>Tu cartera en menús del día</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te da para <b>76 menús</b>" in texto
    assert "De lunes a viernes, comes fuera 15 semanas" in texto
    assert "<i>A unos €13 el menú, con bebida y postre</i>" in texto


def test_formatear_años():
    texto = formatear_menu(Menu(10_000), "eur")

    assert "<b>769 menús</b>" in texto
    assert "comes fuera 2,9 años" in texto


def test_formatear_un_año_justo():
    # 52 semanas son 3.380 €
    assert "comes fuera 1 año\n" in formatear_menu(Menu(3_380), "eur")


def test_formatear_menos_de_una_semana():
    texto = formatear_menu(Menu(30), "eur")

    assert "<b>2 menús</b>" in texto
    assert "comes fuera 2 días" in texto


def test_formatear_uno_y_ninguno():
    texto = formatear_menu(Menu(13), "eur")
    assert "<b>1 menú</b>" in texto
    assert "comes fuera 1 día" in texto
    assert "1 semana" in formatear_menu(Menu(65), "eur")

    texto = formatear_menu(Menu(5), "eur")
    assert "No te da ni para un menú 😅" in texto
    assert "lunes" not in texto
