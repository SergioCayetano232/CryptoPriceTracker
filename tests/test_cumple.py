"""Tests de /cumple."""

from datetime import date

from crypto_tracker.alerts import formatear_cumple
from crypto_tracker.cumple import Cumple


def test_hoy():
    c = Cumple(date(2026, 10, 25))

    assert c.años == 17
    assert c.dias == 6504
    assert c.faltan == 70


def test_la_vispera_y_el_dia():
    assert Cumple(date(2027, 1, 2)).años == 17
    assert Cumple(date(2027, 1, 2)).faltan == 1
    assert Cumple(date(2027, 1, 3)).años == 18
    assert Cumple(date(2027, 1, 3)).faltan == 0


def test_formatear():
    texto = formatear_cumple(Cumple(date(2026, 10, 25)))

    assert "🎂 <b>Bitcoin tiene 17 años</b>" in texto
    assert "lleva 6.504 días funcionando" in texto
    assert "Faltan 70 días para que cumpla 18" in texto


def test_formatear_el_dia():
    texto = formatear_cumple(Cumple(date(2027, 1, 3)))

    assert "tiene 18 años" in texto
    assert "🎉 ¡Hoy es su cumpleaños!" in texto
    assert "Faltan" not in texto
