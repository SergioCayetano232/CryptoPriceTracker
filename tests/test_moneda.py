"""Tests de la moneda de /precio."""

from crypto_tracker.moneda import separar


def test_codigo_al_final():
    assert separar("btc usd") == ("btc", "usd")
    assert separar("btc eth sol GBP") == ("btc eth sol", "gbp")


def test_simbolo_y_nombre():
    assert separar("btc $") == ("btc", "usd")
    assert separar("solana euros") == ("solana", "eur")
    assert separar("eth dólares") == ("eth", "usd")


def test_solo_la_moneda():
    assert separar("usd") == ("", "usd")


def test_sin_moneda():
    assert separar("btc eth") == ("btc eth", None)
    assert separar("") == ("", None)
    assert separar("usd btc") == ("usd btc", None)  # solo cuenta al final
