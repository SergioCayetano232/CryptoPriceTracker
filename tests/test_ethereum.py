"""Tests de /ethereum."""

from datetime import date

from crypto_tracker.alerts import formatear_ethereum
from crypto_tracker.ethereum import Ethereum


def test_hoy():
    e = Ethereum(date(2026, 10, 31))

    assert e.años == 11
    assert e.dias == 4111
    assert e.faltan == 272


def test_la_vispera_y_el_dia():
    assert Ethereum(date(2026, 7, 29)).años == 10
    assert Ethereum(date(2026, 7, 29)).faltan == 1
    assert Ethereum(date(2026, 7, 30)).años == 11
    assert Ethereum(date(2026, 7, 30)).faltan == 0


def test_formatear():
    texto = formatear_ethereum(Ethereum(date(2026, 10, 31)))

    assert "⟠ <b>Ethereum cumple 11 años</b>" in texto
    assert "el 30/07/2015, hace 4.111 días" in texto
    assert "unos 0,31 $" in texto
    assert "Faltan 272 días para que cumpla 12" in texto


def test_formatear_un_año():
    assert "cumple 1 año</b>" in formatear_ethereum(Ethereum(date(2016, 8, 1)))


def test_formatear_el_dia():
    texto = formatear_ethereum(Ethereum(date(2026, 7, 30)))

    assert "🎉 ¡Hoy es su cumpleaños!" in texto
    assert "Faltan" not in texto
