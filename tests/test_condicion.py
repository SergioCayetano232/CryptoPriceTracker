"""Tests de la condición de las /alerta."""

import pytest

from crypto_tracker.condicion import Condicion, CondicionError, leer, separar


@pytest.mark.parametrize(
    "argumento,resto,condicion",
    [
        ("btc 60000 si miedo<20", "btc 60000", Condicion("miedo", True, 20)),
        ("btc 60000 si miedo < 20", "btc 60000", Condicion("miedo", True, 20)),
        (
            "btc 60000 y el miedo por debajo de 20",
            "btc 60000",
            Condicion("miedo", True, 20),
        ),
        ("eth 2000 si rsi>70", "eth 2000", Condicion("rsi", False, 70)),
        ("eth 2000 7d con rsi menos de 30", "eth 2000 7d", Condicion("rsi", True, 30)),
        (
            "eth -10% si RSI está por encima de 65,5",
            "eth -10%",
            Condicion("rsi", False, 65.5),
        ),
        ("btc 60000", "btc 60000", None),
        ("btc 60000 vender la mitad", "btc 60000 vender la mitad", None),
        (
            "btc 70000 vender si sigue subiendo",
            "btc 70000 vender si sigue subiendo",
            None,
        ),
        ("btc 70000 y algo menos de 5", "btc 70000 y algo menos de 5", None),
    ],
)
def test_separar(argumento, resto, condicion):
    assert separar(argumento) == (resto, condicion)


@pytest.mark.parametrize(
    "argumento,error",
    [
        ("btc 60000 si volumen>2", "Solo sé mirar"),
        ("btc 60000 si miedo<120", "de 0 a 100"),
        ("btc 60000 si miedo<veinte", "no es un número"),
        ("btc 60000 si miedo mucho", "No entiendo la condición"),
        ("btc 60000 si miedo<20 vender", "No entiendo la condición"),
    ],
)
def test_separar_malo(argumento, error):
    with pytest.raises(CondicionError, match=error):
        separar(argumento)


def test_cumple():
    assert Condicion("miedo", True, 20).cumple(15)
    assert not Condicion("miedo", True, 20).cumple(20)
    assert Condicion("rsi", False, 70).cumple(71)


def test_guardar_y_leer():
    c = Condicion("rsi", False, 65.5)

    assert c.guardar() == "rsi>65.5"
    assert leer(c.guardar()) == c
    assert leer("miedo<20") == Condicion("miedo", True, 20)


@pytest.mark.parametrize("texto", [None, "", "luna<3", "miedo=20"])
def test_leer_lo_que_no_es(texto):
    assert leer(texto) is None
