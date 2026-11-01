"""Tests de /navidad."""

from datetime import date

from crypto_tracker.alerts import formatear_navidad
from crypto_tracker.navidad import Navidad, navidad

NOVIEMBRE = date(2026, 11, 1)


def test_cuantas():
    assert Navidad(3_000, NOVIEMBRE).cestas == 30
    assert Navidad(100, NOVIEMBRE).cestas == 1
    assert Navidad(99.99, NOVIEMBRE).cestas == 0


def test_navidad():
    assert navidad(NOVIEMBRE) == date(2026, 12, 25)
    assert navidad(date(2026, 12, 25)) == date(2026, 12, 25)
    assert navidad(date(2026, 12, 26)) == date(2027, 12, 25)


def test_faltan():
    assert Navidad(0, NOVIEMBRE).faltan == 54
    assert Navidad(0, date(2026, 12, 24)).faltan == 1
    assert Navidad(0, date(2026, 12, 31)).faltan == 359


def test_formatear():
    texto = formatear_navidad(Navidad(3_000, NOVIEMBRE), "eur")

    assert "🎅 <b>Faltan 54 días para Navidad</b>" in texto
    assert "Tu cartera vale €3.000,00" in texto
    assert "Te da para <b>30 cestas navideñas</b>" in texto
    assert "<i>A unos €100 la cesta, con turrón, embutido y cava</i>" in texto


def test_formatear_miles():
    texto = formatear_navidad(Navidad(500_000, NOVIEMBRE), "eur")
    assert "<b>5.000 cestas navideñas</b>" in texto


def test_formatear_una_y_ninguna():
    texto = formatear_navidad(Navidad(150, NOVIEMBRE), "eur")
    assert "<b>1 cesta navideña</b>" in texto

    texto = formatear_navidad(Navidad(50, NOVIEMBRE), "eur")
    assert "No te da ni para una cesta 😅" in texto


def test_formatear_nochebuena_y_navidad():
    texto = formatear_navidad(Navidad(3_000, date(2026, 12, 24)), "eur")
    assert "🎅 <b>Mañana es Navidad</b>" in texto

    texto = formatear_navidad(Navidad(3_000, date(2026, 12, 25)), "eur")
    assert "🎄 <b>¡Feliz Navidad!</b>" in texto
    assert "Faltan" not in texto
