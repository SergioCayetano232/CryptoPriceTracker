"""Tests de la cartera."""

import pytest

from crypto_tracker.alerts import formatear_cartera
from crypto_tracker.cartera import Valor, total, valorar
from crypto_tracker.config import ConfigError, Posicion, parse_cartera

# --- leer PORTFOLIO ---


def test_leer_cartera():
    cartera = parse_cartera("bitcoin:0.016:1000, Ethereum:0.4:1000,solana:7")

    assert cartera == (
        Posicion("bitcoin", 0.016, 1000.0),
        Posicion("ethereum", 0.4, 1000.0),
        Posicion("solana", 7.0, None),  # sin lo invertido tambien vale
    )


def test_cartera_vacia():
    assert parse_cartera("") == ()


@pytest.mark.parametrize(
    "entrada",
    [
        "bitcoin",  # sin cantidad
        "bitcoin:0",  # cantidad cero
        "bitcoin:-1",
        "bitcoin:mucho",
        "bitcoin:1:-5",  # invertido negativo
        "bitcoin:1:2:3",  # sobra una parte
        ":1",  # sin cripto
        "bitcoin:1,bitcoin:2",  # repetida
    ],
)
def test_cartera_invalida(entrada):
    with pytest.raises(ConfigError):
        parse_cartera(entrada)


# --- valorar ---


def test_valorar():
    cartera = parse_cartera("bitcoin:0.016:1000,ethereum:0.4:1000")
    valores, faltan = valorar(cartera, {"bitcoin": 70000.0, "ethereum": 2250.0})

    assert faltan == []
    assert valores[0].valor == pytest.approx(1120.0)
    assert valores[0].porcentaje == pytest.approx(12.0)
    assert valores[1].ganancia == pytest.approx(-100.0)


def test_valorar_sin_precio():
    cartera = parse_cartera("bitcoin:0.016:1000,solana:7:1000")
    valores, faltan = valorar(cartera, {"bitcoin": 70000.0})

    assert [v.coin_id for v in valores] == ["bitcoin"]
    assert faltan == ["solana"]


def test_total():
    t = total([Valor("bitcoin", 1120.0, 1000.0), Valor("ethereum", 900.0, 1000.0)])

    assert t.valor == pytest.approx(2020.0)
    assert t.ganancia == pytest.approx(20.0)
    assert t.porcentaje == pytest.approx(1.0)


def test_total_si_alguna_no_dice_lo_invertido():
    t = total([Valor("bitcoin", 1120.0, 1000.0), Valor("solana", 1000.0, None)])

    assert t.valor == pytest.approx(2120.0)
    assert t.porcentaje is None


# --- mensaje ---


def test_mensaje_de_la_cartera():
    valores = [Valor("bitcoin", 1120.0, 1000.0), Valor("ethereum", 900.0, 1000.0)]
    texto = formatear_cartera(valores, total(valores), [], "usd")

    assert "Tu cartera" in texto
    assert "$1.120,00" in texto
    assert "+12.00%" in texto
    assert "-10.00%" in texto
    assert "$2.020,00" in texto
    assert "(+$20,00)" in texto


def test_mensaje_con_perdidas():
    valores = [Valor("bitcoin", 800.0, 1000.0)]
    texto = formatear_cartera(valores, total(valores), [], "usd")

    assert "(-$200,00)" in texto
    assert "🔻" in texto


def test_mensaje_avisa_de_lo_que_falta():
    valores = [Valor("bitcoin", 1120.0, 1000.0)]
    texto = formatear_cartera(valores, total(valores), ["solana"], "usd")

    assert "solana" in texto
    assert "no las cuenta" in texto
