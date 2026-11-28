"""Tests de /sesgo."""

from datetime import date, datetime, timezone

import pytest

from crypto_tracker.inversion.movimientos import Movimiento
from crypto_tracker.inversion.sesgo import Grupo, Lado, calcular, dias_hacia_atras
from crypto_tracker.miedo import Indice


def _mov(dia, tipo="compra", cantidad=1.0, coste=100.0, coin_id="bitcoin"):
    cuando = datetime(2026, 10, dia, 23, 30, tzinfo=timezone.utc)
    return Movimiento(dia, coin_id, tipo, cantidad, coste, None, cuando)


def _indice(dia, valor, clase):
    return Indice(valor, clase, date(2026, 10, dia))


INDICES = [
    _indice(1, 10, "Extreme Fear"),
    _indice(2, 30, "Fear"),
    _indice(3, 80, "Extreme Greed"),
    _indice(4, 85, "Extreme Greed"),
    _indice(5, 70, "Greed"),
]


def test_compras_con_codicia_que_van_perdiendo():
    movs = [
        _mov(1, coste=50),  # pagado a 50, hoy a 100: +100%
        _mov(3, coste=200),
        _mov(4, coste=200),  # las dos de euforia a 200: -50%
        _mov(5, coste=125),
    ]

    s = calcular(movs, INDICES, {"bitcoin": 100.0})

    assert s.compras == Lado(
        veces=4,
        media=pytest.approx((10 + 80 + 85 + 70) / 4),
        grupos=[
            Grupo("extreme fear", 1, pytest.approx(100)),
            Grupo("greed", 1, pytest.approx(-20)),
            Grupo("extreme greed", 2, pytest.approx(-50)),
        ],
    )
    assert s.compras.humor == "codicia"
    assert s.ventas is None


def test_ventas_con_miedo():
    movs = [_mov(1, "venta"), _mov(2, "venta"), _mov(2, "venta")]

    s = calcular(movs, INDICES, {"bitcoin": 100.0})

    assert s.ventas.humor == "miedo"
    # De las ventas no digo cómo van: ya no las tienes.
    assert all(g.cambio is None for g in s.ventas.grupos)


def test_neutral():
    lado = Lado(3, 50, [])

    assert lado.humor == "neutral"


def test_pocas_no_tienen_humor():
    s = calcular([_mov(3), _mov(4)], INDICES, {"bitcoin": 100.0})

    assert s.compras.humor is None


def test_cuenta_las_que_no_tienen_indice():
    s = calcular([_mov(1), _mov(20)], INDICES, {"bitcoin": 100.0})

    assert s.compras.veces == 1
    assert s.sin_indice == 1


def test_sin_coste_o_sin_precio_no_cuentan_en_el_cambio():
    movs = [
        _mov(1, coste=None),
        _mov(2, coste=50),
        _mov(2, coste=50, coin_id="pepe"),  # sin precio de hoy
    ]

    s = calcular(movs, INDICES, {"bitcoin": 100.0})

    fear = {g.clase: g for g in s.compras.grupos}
    assert fear["extreme fear"].cambio is None
    assert fear["fear"] == Grupo("fear", 2, pytest.approx(100))


def test_la_fecha_es_la_de_utc():
    # A las 23:30 UTC del día 1 aquí ya es día 2, pero el índice va en UTC.
    s = calcular([_mov(1)], INDICES, {})

    assert s.compras.grupos[0].clase == "extreme fear"


def test_dias_hacia_atras():
    assert dias_hacia_atras([_mov(5), _mov(1)], date(2026, 10, 11)) == 12
