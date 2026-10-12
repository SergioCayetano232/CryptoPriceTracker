"""Tests de /objetivo."""

import pytest

from crypto_tracker.alerts import formatear_objetivo
from crypto_tracker.cartera import valorar
from crypto_tracker.config import parse_cartera
from crypto_tracker.objetivo import Escenario, ObjetivoError, calcular, interpretar


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("bitcoin 100000", ("bitcoin", 100000)),
        ("btc 100k", ("bitcoin", 100000)),
        ("BTC 100.000", ("bitcoin", 100000)),
        ("sol 300€", ("solana", 300)),
        ("sol 300 €", ("solana", 300)),
        ("eth 2500,5", ("ethereum", 2500.5)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


@pytest.mark.parametrize(
    "argumento", ["", "bitcoin", "bitcoin mucho", "btc 0", "a 1 2"]
)
def test_interpretar_formato_malo(argumento):
    with pytest.raises(ObjetivoError, match="/objetivo bitcoin 100000"):
        interpretar(argumento)


def _valores(texto="bitcoin:0.016:1000,solana:7:1000"):
    valores, _ = valorar(parse_cartera(texto), {"bitcoin": 70000.0, "solana": 150.0})
    return valores


def test_calcular_solo_mueve_esa_cripto():
    e = calcular(_valores(), "bitcoin", 100000)

    assert e.ahora == pytest.approx(2170)  # 1120 de bitcoin + 1050 de solana
    assert e.despues == pytest.approx(2650)  # 1600 + 1050
    assert e.cambio == pytest.approx(42.857, abs=0.001)
    assert e.invertido == 2000


def test_calcular_bajando():
    e = calcular(_valores(), "solana", 75)

    assert e.despues == pytest.approx(2170 - 525)


def test_calcular_sin_esa_cripto():
    assert calcular(_valores(), "ethereum", 3000) is None


def test_calcular_sin_lo_invertido():
    e = calcular(_valores("bitcoin:0.016"), "bitcoin", 100000)

    assert e.invertido is None


def test_formatear():
    texto = formatear_objetivo(
        Escenario("bitcoin", 0.016, 70000, 100000, 2170, 2000), "eur"
    )

    assert "Si <b>Bitcoin</b> llega a <b>€100.000,00</b> (+42.86%)" in texto
    assert "valdría <b>€2.650,00</b>" in texto
    assert "+€480,00 respecto a hoy (€2.170,00)" in texto
    assert "Sobre lo invertido, +€650,00 (+32.50%)" in texto
    assert "pasarían de €1.120,00 a €1.600,00" in texto


def test_formatear_sin_invertido_y_perdiendo():
    texto = formatear_objetivo(Escenario("bitcoin", 0.016, 70000, 50000, 1120), "eur")

    assert "🔻 -€320,00 respecto a hoy" in texto
    assert "invertido" not in texto
