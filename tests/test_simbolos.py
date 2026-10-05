"""Tests de los simbolos (btc, eth...) en los comandos."""

import pytest

from crypto_tracker import (
    convertir,
    exportar,
    movimientos,
    periodo,
    puntuales,
    vigiladas,
)
from crypto_tracker.simbolos import IDS, a_id, varias


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("btc", "bitcoin"),
        ("BTC", "bitcoin"),
        (" eth ", "ethereum"),
        ("avax", "avalanche-2"),
        ("bitcoin", "bitcoin"),  # el id de siempre sigue valiendo
        ("Solana", "solana"),
        ("pepe", "pepe"),  # simbolo e id coinciden, no hace falta tabla
        ("cartera", "cartera"),
        ("", ""),
    ],
)
def test_a_id(texto, esperado):
    assert a_id(texto) == esperado


def test_ningun_simbolo_apunta_a_otro_simbolo():
    # Si un id fuese a su vez un simbolo, se traduciria dos veces segun donde.
    assert not set(IDS.values()) & set(IDS)


def test_en_cada_comando():
    assert periodo.interpretar("btc 7d") == ("bitcoin", 168)
    assert exportar.interpretar("eth")[0] == "ethereum"
    assert puntuales.interpretar("sol 150") == ("solana", 150)
    assert puntuales.interpretar_relativa("xrp +10%") == ("ripple", 10)
    assert convertir.interpretar("500 eur sol", "eur").coin_id == "solana"
    assert convertir.interpretar("0.05 btc", "eur").coin_id == "bitcoin"
    assert movimientos.interpretar_compra("btc 0.01 600")[0] == "bitcoin"
    assert movimientos.interpretar_venta("btc todo") == ("bitcoin", None)
    watch, regla = vigiladas.interpretar("sol %5")
    assert (watch.coin_id, regla) == ("solana", "solana:%5.0")


def test_la_alerta_de_cartera_no_se_toca():
    assert puntuales.interpretar("cartera 5000") == ("cartera", 5000)


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("btc eth", ["bitcoin", "ethereum"]),
        ("btc, sol,eth", ["bitcoin", "solana", "ethereum"]),
        ("BTC bitcoin", ["bitcoin"]),  # la misma dos veces
        ("  ", []),
    ],
)
def test_varias(texto, esperado):
    assert varias(texto) == esperado
