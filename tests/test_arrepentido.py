"""Tests de /arrepentido."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.alerts import formatear_arrepentido
from crypto_tracker.arrepentido import Arrepentido, Vendida, calcular
from crypto_tracker.movimientos import Movimiento

AHORA = datetime(2026, 10, 1, tzinfo=timezone.utc)


def _venta(coin_id, cantidad, cobrado):
    return Movimiento(1, coin_id, "venta", cantidad, cobrado, None, AHORA)


def test_suma_por_cripto_y_ordena():
    ventas = [
        _venta("bitcoin", 0.01, 700),
        _venta("solana", 10, 1500),
        _venta("bitcoin", 0.01, 900),
    ]

    a = calcular(ventas, {"bitcoin": 100_000, "solana": 100})

    [btc, sol] = a.vendidas
    assert (btc.coin_id, btc.cantidad, btc.cobrado) == ("bitcoin", 0.02, 1600)
    assert btc.hoy == pytest.approx(2000)
    assert btc.diferencia == pytest.approx(400)
    assert sol.diferencia == pytest.approx(-500)
    assert a.total == pytest.approx(-100)
    assert a.sin_datos == 0


def test_sin_cobrado_o_sin_precio_no_cuenta():
    ventas = [_venta("bitcoin", 0.01, None), _venta("pepe", 1000, 5)]

    a = calcular(ventas, {"bitcoin": 100_000})

    assert a.vendidas == []
    assert a.sin_datos == 2


def test_formatear_vendiste_pronto():
    a = Arrepentido([Vendida("bitcoin", 0.02, 1600, 2000)], 0)

    texto = formatear_arrepentido(a, "eur")

    assert "😩 <b>Bitcoin</b>  +€400,00" in texto
    assert "Vendiste 0,02 por €1.600,00, hoy serían €2.000,00" in texto
    assert "Si no hubieras vendido, hoy tendrías <b>€400,00 más</b>" in texto


def test_formatear_bien_vendido():
    a = Arrepentido(
        [Vendida("bitcoin", 0.02, 1600, 1700), Vendida("solana", 10, 1500, 1000)], 1
    )

    texto = formatear_arrepentido(a, "eur")

    assert "😩 <b>Bitcoin</b>  +€100,00" in texto
    assert "😌 <b>Solana</b>  -€500,00" in texto
    assert "Bien vendido: hoy te darían <b>€400,00 menos</b>" in texto
    assert "No cuento 1 venta" in texto
