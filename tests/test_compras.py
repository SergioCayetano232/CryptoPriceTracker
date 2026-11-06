"""Tests de /compras."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.alerts import formatear_compras
from crypto_tracker.compras import calcular
from crypto_tracker.movimientos import Movimiento

PRECIOS = {"bitcoin": 60000.0, "ethereum": 3000.0}


def _mov(id, coin, cantidad, coste, tipo="compra", dia=1):
    cuando = datetime(2026, 9, dia, 10, tzinfo=timezone.utc)
    return Movimiento(id, coin, tipo, cantidad, coste, None, cuando)


LISTA = [
    _mov(1, "bitcoin", 0.01, 400, dia=1),  # a 40.000: +50%
    _mov(2, "ethereum", 1, 4000, dia=5),  # a 4.000: -25%
    _mov(3, "bitcoin", 0.01, 550, dia=9),  # a 55.000: +9%
]


def test_mejor_y_peor():
    r = calcular(LISTA, PRECIOS)

    assert r.mejor.movimiento.id == 1
    assert r.mejor.pagado == pytest.approx(40000)
    assert r.mejor.cambio == pytest.approx(50)
    assert r.mejor.ganancia == pytest.approx(200)
    assert r.peor.movimiento.id == 2
    assert r.peor.cambio == pytest.approx(-25)
    assert r.peor.ganancia == pytest.approx(-1000)
    assert (r.verdes, r.rojas, r.total, r.sin_precio) == (2, 1, 3, 0)


def test_las_ventas_no_cuentan():
    lista = [*LISTA, _mov(4, "bitcoin", 0.01, 900, tipo="venta")]

    assert calcular(lista, PRECIOS).total == 3


def test_sin_coste_o_sin_precio_de_hoy():
    lista = [*LISTA, _mov(4, "bitcoin", 0.01, None), _mov(5, "solana", 1, 100)]

    assert calcular(lista, PRECIOS).sin_precio == 2


def test_con_empate_la_mas_vieja():
    lista = [_mov(7, "bitcoin", 0.01, 500), _mov(3, "bitcoin", 0.01, 500)]

    assert calcular(lista, PRECIOS).mejor.movimiento.id == 3


def test_nada():
    assert calcular([], PRECIOS) is None
    assert calcular([_mov(1, "bitcoin", 0.01, None)], PRECIOS) is None


def test_formatear():
    texto = formatear_compras(calcular(LISTA, PRECIOS), "eur", None)

    assert "🧾 <b>Tus compras</b>" in texto
    assert "🥇 La mejor: 0,01 de Bitcoin el 01/09/2026 a €40.000,00" in texto
    assert "🔺 +50,0%, <b>+€200,00</b>" in texto
    assert "🥴 La peor: 1 de Ethereum el 05/09/2026 a €4.000,00" in texto
    assert "🔻 -25,0%, <b>-€1.000,00</b>" in texto
    assert "De 3 compras, 2 van ganando y 1 perdiendo" in texto


def test_formatear_de_una_cripto():
    r = calcular(LISTA[::2], PRECIOS)
    texto = formatear_compras(r, "eur", "bitcoin")

    assert "🧾 <b>Tus compras de Bitcoin</b>" in texto
    assert "De 2 compras, las 2 van ganando" in texto


def test_formatear_todas_perdiendo():
    r = calcular(
        [_mov(1, "bitcoin", 0.01, 700), _mov(2, "bitcoin", 0.01, 650)], PRECIOS
    )

    assert "De 2 compras, las 2 van perdiendo" in formatear_compras(r, "eur", None)


def test_formatear_una_sola():
    r = calcular([_mov(1, "bitcoin", 0.01, 400)], PRECIOS)
    texto = formatear_compras(r, "eur", None)

    assert "Solo tienes una compra" in texto
    assert "<i>A precio de hoy, aunque ya la hayas vendido</i>" in texto
    assert "La peor" not in texto


def test_formatear_con_sin_precio():
    lista = [*LISTA, _mov(4, "bitcoin", 0.01, None)]
    texto = formatear_compras(calcular(lista, PRECIOS), "eur", None)

    assert "1 sin lo que costó o sin precio de hoy, no cuenta" in texto
