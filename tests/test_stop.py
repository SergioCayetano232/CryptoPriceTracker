"""Tests de /stop."""

import pytest

from crypto_tracker.cartera import Valor
from crypto_tracker.stop import Stop, StopError, calcular, interpretar


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("eth -15%", ("ethereum", -15.0)),
        ("bitcoin +50%", ("bitcoin", 50.0)),
        ("sol -7,5%", ("solana", -7.5)),
        ("cartera -20%", ("cartera", -20.0)),
    ],
)
def test_interpretar(texto, sale):
    assert interpretar(texto) == sale


@pytest.mark.parametrize(
    "texto, error",
    [
        ("eth", "Escríbelo así"),
        ("eth 2000", "Escríbelo así"),
        ("eth 15%", "¿Perder o ganar?"),
        ("eth -abc%", "no es un porcentaje"),
        ("eth -0%", "no es un porcentaje"),
        ("eth -100%", "100 %"),
    ],
)
def test_interpretar_mal(texto, error):
    with pytest.raises(StopError, match=error):
        interpretar(texto)


def test_sobre_el_precio_medio():
    # 2 ETH que costaron 5.000: 2.500 de media; ahora a 2.700
    s = calcular("ethereum", -15, Valor("ethereum", 5400, 5000, 2))

    assert s.coste == 2500
    assert s.ahora == 2700
    assert s.objetivo == pytest.approx(2125)
    assert not s.sube
    assert s.llevas == pytest.approx(8)
    assert not s.ya_llego


def test_de_ganancia():
    s = calcular("ethereum", 50, Valor("ethereum", 5400, 5000, 2))

    assert s.objetivo == pytest.approx(3750)
    assert s.sube


def test_de_la_cartera_es_sobre_todo_lo_que_metiste():
    s = calcular("cartera", -20, Valor("total", 9000, 10000))

    assert s.objetivo == pytest.approx(8000)
    assert s.llevas == pytest.approx(-10)


@pytest.mark.parametrize(
    "porcentaje, ahora, llego",
    [(-15, 2200, False), (-15, 2125, True), (-15, 2000, True), (20, 3000, True)],
)
def test_ya_llego(porcentaje, ahora, llego):
    assert Stop("ethereum", porcentaje, 2500, ahora).ya_llego == llego


def test_sin_lo_que_te_costo():
    with pytest.raises(StopError, match="lo que te costó"):
        calcular("ethereum", -15, Valor("ethereum", 5400, None, 2))


def test_cartera_sin_lo_que_te_costo():
    with pytest.raises(StopError, match="cada una de tu cartera"):
        calcular("cartera", -15, Valor("total", 9000, None))


@pytest.mark.parametrize(
    "porcentaje, nota",
    [
        (-15, "Stop: -15% sobre lo que te costó"),
        (7.5, "Stop: +7,5% sobre lo que te costó"),
    ],
)
def test_nota(porcentaje, nota):
    assert Stop("ethereum", porcentaje, 2500, 2700).nota == nota
