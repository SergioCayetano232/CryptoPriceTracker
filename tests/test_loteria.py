"""Tests de /loteria."""

from datetime import date

from crypto_tracker.alerts import formatear_loteria
from crypto_tracker.loteria import Loteria, sorteo

NOVIEMBRE = date(2026, 11, 1)


def test_cuantos():
    assert Loteria(1_000, NOVIEMBRE).decimos == 50
    assert Loteria(20, NOVIEMBRE).decimos == 1
    assert Loteria(19.99, NOVIEMBRE).decimos == 0


def test_sorteo():
    assert sorteo(NOVIEMBRE) == date(2026, 12, 22)
    assert sorteo(date(2026, 12, 22)) == date(2026, 12, 22)
    assert sorteo(date(2026, 12, 23)) == date(2027, 12, 22)


def test_faltan():
    assert Loteria(0, NOVIEMBRE).faltan == 51
    assert Loteria(0, date(2026, 12, 21)).faltan == 1
    assert Loteria(0, date(2026, 12, 31)).faltan == 356


def test_formatear():
    texto = formatear_loteria(Loteria(1_000, NOVIEMBRE), "eur")

    assert "🎄 <b>Tu cartera en décimos de Navidad</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te da para <b>50 décimos</b>" in texto
    assert "Faltan 51 días para el sorteo del 22 de diciembre" in texto
    assert "<i>A €20 el décimo</i>" in texto


def test_formatear_miles():
    texto = formatear_loteria(Loteria(100_000, NOVIEMBRE), "eur")
    assert "<b>5.000 décimos</b>" in texto


def test_formatear_uno_y_ninguno():
    assert "<b>1 décimo</b>" in formatear_loteria(Loteria(25, NOVIEMBRE), "eur")
    texto = formatear_loteria(Loteria(10, NOVIEMBRE), "eur")
    assert "No te da ni para un décimo 😅" in texto
    assert "Faltan 51 días" in texto


def test_formatear_un_dia_y_hoy():
    texto = formatear_loteria(Loteria(1_000, date(2026, 12, 21)), "eur")
    assert "Falta 1 día para el sorteo" in texto

    texto = formatear_loteria(Loteria(1_000, date(2026, 12, 22)), "eur")
    assert "🎉 ¡El sorteo es hoy!" in texto
    assert "Faltan" not in texto
