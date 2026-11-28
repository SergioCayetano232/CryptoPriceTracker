"""Tests de /herencia."""

import pytest

from crypto_tracker.herencia import (
    HerenciaError,
    Linea,
    interpretar,
    lineas,
    parece_clave,
)
from crypto_tracker.nucleo.config import Posicion

# Una frase de prueba con la forma de las de verdad (no es de ninguna cartera).
SEMILLA = (
    "abandon ability able about above absent absorb abstract absurd abuse "
    "access accident"
)


@pytest.mark.parametrize(
    "texto",
    [
        SEMILLA,
        SEMILLA.upper(),
        SEMILLA + " account accuse achieve acid acoustic acquire across act action "
        "actor actress actual",
        "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ",  # WIF de ejemplo
        "e9873d79c6d87dc0fb6a5778633389f4453213303da61f20bd67fc233aa33262",
        "xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJ",
        "mi clave es xprv9s21ZrQH143K3QT",
    ],
)
def test_parece_clave(texto):
    assert parece_clave(texto)


@pytest.mark.parametrize(
    "texto",
    [
        "Ledger en el cajón del escritorio",
        "En Binance, con el correo de siempre. Mi hermana sabe la contraseña del "
        "ordenador y dónde está el papel con lo demás",
        "bc1p5d7rjq7g6rdk2yhzks9smlaqtedr4dekq08ge8ztwac72sfr9rusxg3297",  # dirección
        "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        "abandon ability able",  # unas pocas no son una frase
    ],
)
def test_no_parece_clave(texto):
    assert not parece_clave(texto)


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("", ("ver",)),
        ("btc Ledger en el cajón", ("donde", "bitcoin", "Ledger en el cajón")),
        ("eth no", ("donde", "ethereum", None)),
        ("nota Habla con mi hermana", ("nota", "Habla con mi hermana")),
        ("nota quitar", ("nota", None)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


def test_no_guarda_una_semilla():
    with pytest.raises(HerenciaError, match="no la guardo"):
        interpretar(f"btc {SEMILLA}")
    with pytest.raises(HerenciaError, match="no la guardo"):
        interpretar(f"nota {SEMILLA}")


def test_interpretar_malo():
    with pytest.raises(HerenciaError, match="Escríbelo así"):
        interpretar("btc")
    with pytest.raises(HerenciaError, match="muy largo"):
        interpretar("btc " + "en el cajón " * 30)


def test_lineas():
    cartera = [
        Posicion("ethereum", 1.0, 2000),
        Posicion("bitcoin", 0.01, 500),
        Posicion("pepe", 1000, 10),
        Posicion("solana", 0, 0),  # vendida entera
    ]

    lista = lineas(
        cartera, {"bitcoin": 60000.0, "ethereum": 3000.0}, {"bitcoin": "Ledger"}
    )

    assert lista == [
        Linea("ethereum", 1.0, 3000.0, None),
        Linea("bitcoin", 0.01, 600.0, "Ledger"),
        Linea("pepe", 1000, None, None),
    ]
