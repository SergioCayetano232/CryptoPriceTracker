"""Tests de /mercado."""

import pytest

from crypto_tracker.mercado import Mercado, grande, leer


def _datos(**cambios):
    data = {
        "total_market_cap": {"eur": 2.5e12, "usd": 2.9e12},
        "market_cap_change_percentage_24h_usd": -4.31,
        "market_cap_percentage": {"btc": 58.8, "eth": 11.0, "usdt": 6.5, "usdc": 2.6},
    }
    return {"data": {**data, **cambios}}


def test_leer():
    assert leer(_datos(), "eur") == Mercado(
        2.5e12, -4.31, 58.8, 11.0, pytest.approx(9.1)
    )
    assert leer(_datos(), "USD").total == 2.9e12


def test_leer_sin_una_estable_no_suma():
    # Sumar solo una daria un numero que parece completo y no lo es.
    datos = _datos(market_cap_percentage={"btc": 58.8, "usdt": 6.5})

    mercado = leer(datos, "eur")

    assert mercado.estables is None
    assert mercado.ethereum is None


def test_leer_lo_raro():
    datos = _datos(total_market_cap=None, market_cap_change_percentage_24h_usd="x")

    mercado = leer(datos, "eur")

    assert mercado.total is None
    assert mercado.variacion is None
    assert mercado.bitcoin == 58.8


@pytest.mark.parametrize("datos", [{}, [], {"data": None}, {"data": "no"}])
def test_leer_algo_que_no_es_lo_esperado(datos):
    assert leer(datos, "eur") == Mercado(None, None, None, None, None)


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (2_507_117_360_729, "2,51 billones"),
        (1e12, "1,00 billones"),
        (850_000_000_000, "850.000 millones"),
        (3_400_000_000, "3.400 millones"),
    ],
)
def test_grande(valor, esperado):
    assert grande(valor) == esperado
