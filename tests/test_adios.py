"""Tests de /adios."""

from datetime import date

from crypto_tracker.adios import Adios
from crypto_tracker.alerts import formatear_adios


def test_hoy():
    a = Adios(date(2026, 10, 27))

    assert a.años == 15
    assert a.dias == 5798
    assert a.faltan == 46


def test_la_vispera_y_el_dia():
    assert Adios(date(2026, 12, 11)).años == 15
    assert Adios(date(2026, 12, 11)).faltan == 1
    assert Adios(date(2026, 12, 12)).años == 16
    assert Adios(date(2026, 12, 12)).faltan == 0


def test_formatear():
    texto = formatear_adios(Adios(date(2026, 10, 27)))

    assert "👻 <b>Satoshi lleva 15 años sin aparecer</b>" in texto
    assert "el 12/12/2010, hace 5.798 días" in texto
    assert "Faltan 46 días para que se cumplan 16" in texto


def test_formatear_un_año():
    assert "lleva 1 año sin" in formatear_adios(Adios(date(2012, 1, 1)))


def test_formatear_el_dia():
    texto = formatear_adios(Adios(date(2026, 12, 12)))

    assert "Hoy hace 16 años de su último mensaje" in texto
    assert "Faltan" not in texto
