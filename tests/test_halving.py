"""Tests de /halving."""

from datetime import date

import pytest

from crypto_tracker.alerts import formatear_halving
from crypto_tracker.halving import calcular


def test_el_siguiente():
    h = calcular(date(2026, 10, 25))

    assert h.anterior == date(2024, 4, 20)
    assert h.siguiente == date(2028, 4, 17)
    assert h.recompensa == 3.125
    assert h.faltan == 540


def test_lo_que_va_de_ciclo():
    assert calcular(date(2024, 4, 20)).hecho == 0
    assert calcular(date(2026, 4, 19)).hecho == pytest.approx(50, abs=0.1)


def test_pasado_el_de_2028_salta_al_siguiente():
    h = calcular(date(2028, 5, 1))

    assert h.anterior == date(2028, 4, 17)
    assert h.siguiente == date(2032, 4, 14)
    assert h.recompensa == 1.5625


def test_el_mismo_dia_ya_cuenta_como_pasado():
    assert calcular(date(2028, 4, 17)).anterior == date(2028, 4, 17)


def test_formatear():
    texto = formatear_halving(calcular(date(2026, 10, 25)))

    assert "Faltan <b>540 días</b>, hacia el 17/04/2028" in texto
    assert "63% del ciclo" in texto
    assert "bajará de 3,125 a 1,5625 BTC" in texto


def test_formatear_un_dia():
    assert "Faltan <b>1 día</b>" in formatear_halving(calcular(date(2028, 4, 16)))


def test_formatear_el_dia_que_toca():
    assert "toca hoy" in formatear_halving(calcular(date(2028, 4, 17)))
    assert "toca hoy" not in formatear_halving(calcular(date(2028, 4, 18)))
