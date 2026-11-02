"""Tests de /nochevieja."""

from datetime import date

import pytest

from crypto_tracker.alerts import formatear_nochevieja
from crypto_tracker.comandos import interpretar
from crypto_tracker.nochevieja import Nochevieja

NOVIEMBRE = date(2026, 11, 2)


def test_faltan():
    assert Nochevieja(0, NOVIEMBRE).faltan == 59
    assert Nochevieja(0, date(2026, 12, 30)).faltan == 1
    assert Nochevieja(0, date(2026, 12, 31)).faltan == 0
    assert Nochevieja(0, date(2027, 1, 1)).faltan == 364


def test_pasado():
    assert Nochevieja(0, date(2026, 1, 1)).pasado == 0
    assert Nochevieja(0, NOVIEMBRE).pasado == pytest.approx(305 / 365 * 100)
    # 2028 es bisiesto: el 2 de julio es la mitad justa, 183 de 366.
    assert Nochevieja(0, date(2028, 7, 2)).pasado == pytest.approx(50)


def test_botellas():
    assert Nochevieja(3_000, NOVIEMBRE).botellas == 300
    assert Nochevieja(9.99, NOVIEMBRE).botellas == 0


def test_formatear():
    texto = formatear_nochevieja(Nochevieja(3_000, NOVIEMBRE), "eur")

    assert "🥂 <b>Faltan 59 días para Nochevieja</b>" in texto
    assert "▰▰▰▰▰▰▰▰▱▱ llevas el 84% del año" in texto
    assert "Tu cartera vale €3.000,00" in texto
    assert "Te da para <b>300 botellas de cava</b>" in texto
    assert "<i>A unos €10 la botella, de supermercado</i>" in texto


def test_formatear_dias_especiales():
    assert "🎉 <b>¡Hoy es Nochevieja!</b>" in formatear_nochevieja(
        Nochevieja(100, date(2026, 12, 31)), "eur"
    )
    assert "🍇 <b>Mañana es Nochevieja</b>" in formatear_nochevieja(
        Nochevieja(100, date(2026, 12, 30)), "eur"
    )


def test_formatear_una_ninguna_y_miles():
    assert "<b>1 botella de cava</b>" in formatear_nochevieja(
        Nochevieja(15, NOVIEMBRE), "eur"
    )
    assert "No te da ni para una botella 😅" in formatear_nochevieja(
        Nochevieja(5, NOVIEMBRE), "eur"
    )
    assert "<b>10.000 botellas de cava</b>" in formatear_nochevieja(
        Nochevieja(100_000, NOVIEMBRE), "eur"
    )


def test_comando():
    assert interpretar("/nochevieja") == ("nochevieja", "")
    assert interpretar("/findeaño") == ("nochevieja", "")
    assert interpretar("/uvas") == ("nochevieja", "")
