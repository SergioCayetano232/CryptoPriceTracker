"""Tests de /primera."""

from datetime import date, datetime, timezone

import pytest

from crypto_tracker.alerts import formatear_primera
from crypto_tracker.movimientos import Movimiento
from crypto_tracker.primera import Primera, buscar

MARZO = datetime(2026, 3, 12, 10, 0, tzinfo=timezone.utc)


def _mov(id, tipo="compra", coste=600.0, cantidad=0.01):
    return Movimiento(id, "bitcoin", tipo, cantidad, coste, None, MARZO)


def test_busca_la_compra_mas_vieja():
    lista = [_mov(5), _mov(3, "venta"), _mov(2), _mov(1, "venta")]

    assert buscar(lista).id == 2


def test_sin_compras():
    assert buscar([_mov(1, "venta")]) is None
    assert buscar([]) is None


def test_cuanto_ha_cambiado():
    p = Primera(_mov(1), 70000.0, date(2026, 10, 26))

    assert p.dias == 228
    assert p.pagado == pytest.approx(60000)
    assert p.cambio == pytest.approx(16.667, abs=0.001)


def test_sin_coste_o_sin_precio():
    assert Primera(_mov(1, coste=None), 70000.0, date(2026, 10, 26)).cambio is None
    assert Primera(_mov(1), None, date(2026, 10, 26)).cambio is None


def test_formatear():
    texto = formatear_primera(Primera(_mov(1), 70000.0, date(2026, 10, 26)), "eur")

    assert texto.startswith("🥇 <b>Tu primera compra</b>\n")
    assert "0,01 de Bitcoin por €600,00 (a €60.000,00)" in texto
    assert "el 12/03/2026, hace 228 días" in texto
    assert "🔺 Ahora está a €70.000,00: <b>+16.67%</b> desde entonces" in texto
    assert "Lo que compraste vale hoy €700,00 (+€100,00)" in texto


def test_formatear_hoy_y_sin_coste():
    hoy = MARZO.astimezone().date()
    texto = formatear_primera(Primera(_mov(1, coste=None), 70000.0, hoy), "eur")

    assert ", hoy" in texto
    assert "por €" not in texto
    assert "desde entonces" not in texto
    assert "Lo que compraste vale hoy €700,00" in texto
