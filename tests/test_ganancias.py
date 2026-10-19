"""Tests de /ganancias."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.alerts import formatear_ganancias
from crypto_tracker.config import Posicion
from crypto_tracker.ganancias import calcular, de_venta
from crypto_tracker.movimientos import Movimiento

AHORA = datetime(2026, 10, 1, tzinfo=timezone.utc)


def _venta(coin_id, cantidad, cobrado, antes):
    return Movimiento(1, coin_id, "venta", cantidad, cobrado, antes, AHORA)


def test_de_venta_al_precio_medio():
    # 0,02 que costaron 1.000: la mitad costó 500 y se vende por 700
    assert de_venta(Posicion("bitcoin", 0.02, 1000), 0.01, 700) == pytest.approx(200)


def test_de_venta_perdiendo():
    assert de_venta(Posicion("solana", 10, 2000), 10, 1500) == pytest.approx(-500)


@pytest.mark.parametrize(
    "antes, cobrado",
    [
        (Posicion("bitcoin", 0.02, 1000), None),  # de antes de apuntar el precio
        (Posicion("bitcoin", 0.02, None), 700),  # no se sabe lo que costó
        (None, 700),
    ],
)
def test_de_venta_sin_datos(antes, cobrado):
    assert de_venta(antes, 0.01, cobrado) is None


def test_calcular_suma_por_cripto_y_ordena():
    ventas = [
        _venta("solana", 5, 600, Posicion("solana", 10, 2000)),  # -400
        _venta("bitcoin", 0.01, 700, Posicion("bitcoin", 0.02, 1000)),  # +200
        _venta("bitcoin", 0.01, 650, Posicion("bitcoin", 0.01, 500)),  # +150
        _venta("ethereum", 1, None, Posicion("ethereum", 2, 4000)),
    ]

    g = calcular(ventas)

    assert [c for c, _ in g.por_cripto] == ["bitcoin", "solana"]
    assert g.por_cripto[0][1] == pytest.approx(350)
    assert g.total == pytest.approx(-50)
    assert g.sin_datos == 1


def test_calcular_sin_ventas():
    g = calcular([])

    assert g.por_cripto == []
    assert g.total == 0
    assert g.sin_datos == 0


def test_porcentaje_sobre_lo_que_costo():
    ventas = [
        _venta("solana", 5, 600, Posicion("solana", 10, 2000)),  # costó 1.000
        _venta("bitcoin", 0.01, 700, Posicion("bitcoin", 0.02, 1000)),  # costó 500
        _venta("bitcoin", 0.01, 650, Posicion("bitcoin", 0.01, 500)),  # costó 500
    ]

    g = calcular(ventas)

    assert g.porcentaje("bitcoin") == pytest.approx(35)
    assert g.porcentaje("solana") == pytest.approx(-40)
    assert g.porcentaje_total == pytest.approx(-2.5)


def test_porcentaje_si_no_costo_nada():
    g = calcular([_venta("bitcoin", 0.01, 700, Posicion("bitcoin", 0.02, 0))])

    assert g.porcentaje("bitcoin") is None
    assert g.porcentaje_total is None


def test_formatear_con_el_porcentaje():
    ventas = [
        _venta("solana", 5, 600, Posicion("solana", 10, 2000)),
        _venta("bitcoin", 0.01, 700, Posicion("bitcoin", 0.02, 1000)),
    ]

    texto = formatear_ganancias(calcular(ventas), "eur")

    assert "🔺 <b>Bitcoin</b>  +€200,00  <i>+40.00%</i>" in texto
    assert "🔻 <b>Solana</b>  -€400,00  <i>-40.00%</i>" in texto
    assert "Total <b>-€200,00</b>  <i>-13.33%</i>" in texto
