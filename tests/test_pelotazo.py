"""Tests de /pelotazo."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.alerts import formatear_pelotazo
from crypto_tracker.movimientos import Movimiento
from crypto_tracker.pelotazo import calcular

CUANDO = datetime(2025, 3, 15, 12, tzinfo=timezone.utc)


def _mov(coin_id, cantidad, coste, tipo="compra"):
    return Movimiento(1, coin_id, tipo, cantidad, coste, None, CUANDO)


def test_mejor_y_peor():
    movs = [
        _mov("bitcoin", 0.01, 500),  # hoy 1.000: +100%
        _mov("solana", 10, 2000),  # hoy 1.000: -50%
        _mov("bitcoin", 0.01, 800),  # hoy 1.000: +25%
    ]

    p = calcular(movs, {"bitcoin": 100_000, "solana": 100})

    assert p.mejor.compra.coste == 500
    assert p.mejor.cambio == pytest.approx(100)
    assert p.peor.compra.coin_id == "solana"
    assert p.peor.cambio == pytest.approx(-50)


def test_una_sola_no_tiene_peor():
    p = calcular([_mov("bitcoin", 0.01, 500)], {"bitcoin": 100_000})

    assert p.peor is None


def test_no_cuenta_ventas_recompensas_ni_sin_precio():
    movs = [
        _mov("bitcoin", 0.01, 500, "venta"),
        _mov("ethereum", 0.1, 0, "recompensa"),
        _mov("pepe", 1000, 5),
    ]

    assert calcular(movs, {"bitcoin": 100_000, "ethereum": 3000}) is None


def test_formatear():
    movs = [_mov("bitcoin", 0.01, 500), _mov("solana", 10, 2000)]
    texto = formatear_pelotazo(
        calcular(movs, {"bitcoin": 100_000, "solana": 100}), "eur"
    )

    assert "🎯 <b>Tu pelotazo: Bitcoin +100.00%</b>" in texto
    assert "0,01 por €500,00 el 15/03/2025, hoy valen €1.000,00" in texto
    assert "🤦 <b>Tu peor compra: Solana -50.00%</b>" in texto


def test_formatear_una_sola():
    p = calcular([_mov("bitcoin", 0.01, 500)], {"bitcoin": 100_000})

    assert "peor compra" not in formatear_pelotazo(p, "eur")


def test_formatear_sin_compras():
    assert "No tengo compras" in formatear_pelotazo(None, "eur")
