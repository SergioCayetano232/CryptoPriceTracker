"""Tests de la cartera."""

from datetime import timedelta

import pytest

from crypto_tracker.alerts import formatear_cartera
from crypto_tracker.cartera import Valor, serie_valor, total, valor_total, valorar
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


def test_valor_total():
    posiciones = [Posicion("bitcoin", 0.02, 1000), Posicion("ethereum", 0.5)]
    precios = {"bitcoin": 50000.0, "ethereum": 2000.0}

    assert valor_total(posiciones, precios) == 2000


def test_valor_total_sin_alguna_no_da_total():
    posiciones = [Posicion("bitcoin", 0.02), Posicion("ethereum", 0.5)]

    assert valor_total(posiciones, {"bitcoin": 50000.0}) is None


def test_valor_total_sin_cartera():
    assert valor_total([], {"bitcoin": 50000.0}) is None


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


def test_precio_medio():
    cartera = parse_cartera("bitcoin:0.016:1000,solana:7,ethereum:0.4:0")
    valores, _ = valorar(cartera, {"bitcoin": 70000.0, "solana": 150.0, "ethereum": 1})

    assert valores[0].precio_medio == pytest.approx(62500.0)
    assert valores[0].precio == pytest.approx(70000.0)
    assert valores[1].precio_medio is None  # sin lo que costo no hay media
    assert valores[2].precio_medio is None  # regalada: una media de 0 no dice nada


def test_el_total_no_tiene_precio_medio():
    valores = [Valor("bitcoin", 1120.0, 1000.0, 0.016)]

    assert total(valores).precio_medio is None


def test_mensaje_con_precio_medio():
    valores = [Valor("bitcoin", 1120.0, 1000.0, 0.016), Valor("solana", 1050.0)]
    texto = formatear_cartera(valores, total(valores), [], "eur")

    assert "<i>Te salió a €62.500,00 · ahora €70.000,00</i>" in texto
    assert texto.count("Te salió") == 1


def test_mensaje_avisa_de_lo_que_falta():
    valores = [Valor("bitcoin", 1120.0, 1000.0)]
    texto = formatear_cartera(valores, total(valores), ["solana"], "usd")

    assert "solana" in texto
    assert "no las cuenta" in texto


# --- lo que ha valido en el tiempo ---


def _h(horas):
    from datetime import datetime, timezone

    return datetime(2026, 10, 1, 12, tzinfo=timezone.utc) + timedelta(hours=horas)


def test_serie_valor_suma_cada_consulta():
    posiciones = [Posicion("bitcoin", 0.5), Posicion("ethereum", 2)]
    filas = [
        (_h(0), "bitcoin", 60000.0),
        (_h(0), "ethereum", 2000.0),
        (_h(1), "bitcoin", 62000.0),
        (_h(1), "ethereum", 2100.0),
    ]

    assert serie_valor(posiciones, filas) == [(_h(0), 34000.0), (_h(1), 35200.0)]


def test_serie_valor_ignora_lo_que_no_tienes():
    filas = [(_h(0), "bitcoin", 60000.0), (_h(0), "solana", 150.0)]

    assert serie_valor([Posicion("bitcoin", 1)], filas) == [(_h(0), 60000.0)]


def test_serie_valor_espera_a_tener_todas():
    # ethereum se empezo a guardar mas tarde: antes no hay valor completo
    posiciones = [Posicion("bitcoin", 1), Posicion("ethereum", 1)]
    filas = [
        (_h(0), "bitcoin", 60000.0),
        (_h(1), "bitcoin", 61000.0),
        (_h(1), "ethereum", 2000.0),
    ]

    assert serie_valor(posiciones, filas) == [(_h(1), 63000.0)]


def test_serie_valor_aguanta_un_hueco_corto():
    # una consulta en la que no vino ethereum: se tira del de hace 5 min
    posiciones = [Posicion("bitcoin", 1), Posicion("ethereum", 1)]
    filas = [
        (_h(0), "bitcoin", 60000.0),
        (_h(0), "ethereum", 2000.0),
        (_h(1 / 12), "bitcoin", 60500.0),
    ]

    assert serie_valor(posiciones, filas)[-1] == (_h(1 / 12), 62500.0)


def test_serie_valor_no_tira_de_precios_viejos():
    # ethereum solo se guardo hace dos dias, con un /status suelto
    posiciones = [Posicion("bitcoin", 1), Posicion("ethereum", 1)]
    filas = [
        (_h(0), "ethereum", 2000.0),
        (_h(48), "bitcoin", 60000.0),
    ]

    assert serie_valor(posiciones, filas) == []


def test_serie_valor_sin_cartera():
    assert serie_valor([], [(_h(0), "bitcoin", 60000.0)]) == []
