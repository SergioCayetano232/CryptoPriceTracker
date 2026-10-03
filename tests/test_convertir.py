"""Tests de /convertir."""

import pytest

from crypto_tracker.convertir import Conversion, ConvertirError, interpretar


@pytest.mark.parametrize(
    "argumento, esperado",
    [
        ("0.05 bitcoin", Conversion(0.05, "bitcoin", False)),
        ("0,05 Bitcoin", Conversion(0.05, "bitcoin", False)),
        ("0.05 bitcoin en euros", Conversion(0.05, "bitcoin", False)),
        ("0.05 bitcoin eur", Conversion(0.05, "bitcoin", False)),
        ("500 eur solana", Conversion(500, "solana", True)),
        ("500 EUR a solana", Conversion(500, "solana", True)),
        ("500 € solana", Conversion(500, "solana", True)),
        ("500€ solana", Conversion(500, "solana", True)),
        ("€500 solana", Conversion(500, "solana", True)),
        ("1.000 euros en solana", Conversion(1000, "solana", True)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento, "eur") == esperado


def test_interpretar_en_dolares():
    assert interpretar("500$ solana", "usd") == Conversion(500, "solana", True)
    assert interpretar("500 dólares solana", "usd") == Conversion(500, "solana", True)


@pytest.mark.parametrize("argumento", ["", "bitcoin", "0.05", "1 2 3 4"])
def test_interpretar_formato_malo(argumento):
    with pytest.raises(ConvertirError, match="/convertir 0.05 bitcoin"):
        interpretar(argumento, "eur")


@pytest.mark.parametrize("argumento", ["mucho bitcoin", "0 bitcoin", "-1 bitcoin"])
def test_interpretar_cantidad_mala(argumento):
    with pytest.raises(ConvertirError, match="no es una cantidad"):
        interpretar(argumento, "eur")


@pytest.mark.parametrize(
    "argumento", ["500 usd solana", "500$ solana", "5 dólares btc"]
)
def test_otra_moneda(argumento):
    with pytest.raises(ConvertirError, match="en EUR, no en USD"):
        interpretar(argumento, "eur")


def test_resultado():
    assert Conversion(0.05, "bitcoin", False).resultado(62000.0) == 3100
    assert Conversion(300, "solana", True).resultado(150.0) == 2
