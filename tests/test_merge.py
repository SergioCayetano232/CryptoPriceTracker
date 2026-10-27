"""Tests de /merge."""

from datetime import date

from crypto_tracker.alerts import formatear_merge
from crypto_tracker.merge import Merge


def test_hoy():
    m = Merge(date(2026, 10, 27))

    assert m.años == 4
    assert m.dias == 1503
    assert m.faltan == 323


def test_la_vispera_y_el_dia():
    assert Merge(date(2026, 9, 14)).años == 3
    assert Merge(date(2026, 9, 14)).faltan == 1
    assert Merge(date(2026, 9, 15)).años == 4
    assert Merge(date(2026, 9, 15)).faltan == 0


def test_formatear():
    texto = formatear_merge(Merge(date(2026, 10, 27)))

    assert "🐼 <b>The Merge cumple 4 años</b>" in texto
    assert "el 15/09/2022, hace 1.503 días" in texto
    assert "un 99,95 % menos de energía" in texto
    assert "Faltan 323 días para que cumpla 5" in texto


def test_formatear_un_año():
    assert "cumple 1 año</b>" in formatear_merge(Merge(date(2023, 10, 1)))


def test_formatear_el_dia():
    texto = formatear_merge(Merge(date(2026, 9, 15)))

    assert "🎉 ¡Hoy es su aniversario!" in texto
    assert "Faltan" not in texto
