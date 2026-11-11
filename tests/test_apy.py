"""Tests de /apy."""

import pytest

from crypto_tracker.alerts import formatear_apy
from crypto_tracker.apy import ApyError, Peticion, calcular, interpretar


def test_los_años_de_siempre():
    tramos = calcular(2, 4)

    assert [t.años for t in tramos] == [1, 3, 5, 10]
    assert tramos[0].cantidad == pytest.approx(2.08)
    assert tramos[0].ganado == pytest.approx(0.08)
    assert tramos[-1].cantidad == pytest.approx(2 * 1.04**10)


def test_solo_los_años_que_dices():
    [t] = calcular(10, 10, 2)

    assert t.años == 2
    assert t.cantidad == pytest.approx(12.1)


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("eth 4%", Peticion("ethereum", 4)),
        ("2 eth 4%", Peticion("ethereum", 4, 2)),
        ("eth al 4% 5a", Peticion("ethereum", 4, años=5)),
        ("eth 4% 5 años", Peticion("ethereum", 4, años=5)),
        ("sol 7,5% 1 año", Peticion("solana", 7.5, años=1)),
        ("4% 0.5 btc 10años", Peticion("bitcoin", 4, 0.5, 10)),
        ("algorand 6%", Peticion("algorand", 6)),
    ],
)
def test_interpretar(texto, esperado):
    assert interpretar(texto) == esperado


@pytest.mark.parametrize(
    "texto,error",
    [
        ("", "Escríbelo así"),
        ("eth", "Escríbelo así"),
        ("4%", "Escríbelo así"),
        ("eth 0%", "no es un interés"),
        ("eth mucho%", "no es un interés"),
        ("eth 4% 0a", "De 1 a 50"),
        ("eth 4% 60a", "De 1 a 50"),
        ("-2 eth 4%", "no es una cantidad"),
        ("eth sol 4%", "No entiendo 'sol'"),
    ],
)
def test_interpretar_mal(texto, error):
    with pytest.raises(ApyError, match=error):
        interpretar(texto)


def test_formatear():
    texto = formatear_apy("ETH", 2, 4, calcular(2, 4), 2400.0, "eur", de_cartera=True)

    assert texto.startswith("🌱 <b>2 ETH al 4% al año</b> (lo de tu cartera)\n\n")
    assert "En 1 año: <b>2,08 ETH</b> (+0,08) · €4.992,00" in texto
    assert "En 10 años: <b>2,96049 ETH</b> (+0,960489)" in texto
    assert "A €2.400,00, el precio de hoy" in texto


def test_formatear_sin_precio():
    texto = formatear_apy("SOL", 10, 7.5, calcular(10, 7.5, 5), None, "eur")

    assert texto.startswith("🌱 <b>10 SOL al 7,5% al año</b>\n\n")
    assert "En 5 años: <b>14,3563 SOL</b> (+4,35629)" in texto
    assert "€" not in texto
