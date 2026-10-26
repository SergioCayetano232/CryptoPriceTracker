"""Tests de /whitepaper."""

from datetime import date

from crypto_tracker.alerts import formatear_whitepaper
from crypto_tracker.whitepaper import Whitepaper


def test_hoy():
    w = Whitepaper(date(2026, 10, 26))

    assert w.años == 17
    assert w.dias == 6569
    assert w.faltan == 5


def test_la_vispera_y_el_dia():
    assert Whitepaper(date(2026, 10, 30)).años == 17
    assert Whitepaper(date(2026, 10, 30)).faltan == 1
    assert Whitepaper(date(2026, 10, 31)).años == 18
    assert Whitepaper(date(2026, 10, 31)).faltan == 0


def test_el_dia_despues():
    w = Whitepaper(date(2026, 11, 1))

    assert w.años == 18
    assert w.faltan == 364


def test_formatear():
    texto = formatear_whitepaper(Whitepaper(date(2026, 10, 26)))

    assert "📄 <b>El whitepaper de Bitcoin tiene 17 años</b>" in texto
    assert "hace 6.569 días" in texto
    assert "Faltan 5 días para que cumpla 18" in texto


def test_formatear_el_dia():
    texto = formatear_whitepaper(Whitepaper(date(2026, 10, 31)))

    assert "tiene 18 años" in texto
    assert "🎉 ¡Hoy es su cumpleaños!" in texto
    assert "Faltan" not in texto
