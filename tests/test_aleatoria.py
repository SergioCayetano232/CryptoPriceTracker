"""Tests de /aleatoria."""

import random

from crypto_tracker.aleatoria import elegir, es_estable
from crypto_tracker.alerts import formatear_aleatoria
from crypto_tracker.top import Movida


def _m(coin_id, simbolo, precio=1.0, variacion=0.0):
    return Movida(coin_id, coin_id.title(), simbolo, precio, variacion)


LISTA = [
    _m("bitcoin", "BTC"),
    _m("tether", "USDT"),
    _m("ethereum", "ETH"),
    _m("dai", "DAI"),
    _m("solana", "SOL"),
]


def test_estables():
    assert es_estable(_m("tether", "USDT"))
    assert es_estable(_m("first-digital-usd", "FDUSD"))
    assert es_estable(_m("dai", "DAI"))
    assert es_estable(_m("blackrock-usd-institutional-digital-liquidity-fund", "BUIDL"))
    assert not es_estable(_m("bitcoin", "BTC"))


def test_ni_estables_ni_las_que_vigilas():
    salen = {elegir(LISTA, {"bitcoin"}, random.Random(i))[1].coin_id for i in range(50)}

    assert salen == {"ethereum", "solana"}


def test_el_puesto_cuenta_tambien_las_que_no_salen():
    puesto, m = elegir(LISTA, {"bitcoin", "ethereum"})

    assert (puesto, m.coin_id) == (5, "solana")


def test_sin_candidatas():
    assert elegir(LISTA, {"bitcoin", "ethereum", "solana"}) is None
    assert elegir([], set()) is None


def test_formatear():
    texto = formatear_aleatoria(5, _m("solana", "SOL", 105.91, -2.5), "usd")

    assert "🎲 <b>Solana (SOL)</b>" in texto
    assert "Es la número 5 por tamaño" in texto
    assert "Vale $105,91  ·  En 24 h: 🔻 -2.50%" in texto
    assert "/vigilar solana %5" in texto


def test_formatear_sin_repetir_el_simbolo():
    texto = formatear_aleatoria(83, Movida("nexo", "NEXO", "NEXO", 0.8, 0.3), "usd")

    assert "🎲 <b>NEXO</b>" in texto
