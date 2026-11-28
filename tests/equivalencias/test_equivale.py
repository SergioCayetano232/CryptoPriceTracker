"""Tests de /equivale."""

import pytest

from crypto_tracker.equivalencias.equivale import COSAS, OTROS_NOMBRES, elegir
from crypto_tracker.nucleo.comandos import COMANDOS


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("cafe", "cafe"),
        ("Café", "cafe"),
        ("  KEBAB ", "kebab"),
        ("cañas", "cana"),
        ("iphones", "iphone"),
        ("kebabs", "kebab"),
        ("croquetas", "croquetas"),  # ya va en plural
        ("jamones", "jamon"),
        ("cerveza", "cana"),
        ("Big Mac", "bigmac"),
        ("lamborghini", "lambo"),
    ],
)
def test_elegir(texto, esperado):
    assert elegir(texto) == esperado


@pytest.mark.parametrize("texto", ["", "bitcoin", "pizza", "s", "es"])
def test_elegir_lo_que_no_es(texto):
    assert elegir(texto) is None


def test_todas_son_comandos_que_existen():
    assert set(COSAS) <= set(COMANDOS)
    assert set(OTROS_NOMBRES.values()) <= set(COSAS)
    assert len(COSAS) == len(set(COSAS))
