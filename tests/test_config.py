"""Tests del parseo del .env."""

import pytest

from crypto_tracker.config import ConfigError, _parse_watchlist


def test_formato_paso():
    watches = _parse_watchlist("bitcoin:1000")

    assert len(watches) == 1
    assert watches[0].coin_id == "bitcoin"
    assert watches[0].step == 1000
    assert watches[0].min_price is None


def test_formato_rango():
    watches = _parse_watchlist("bitcoin:55000:75000")

    assert watches[0].min_price == 55000
    assert watches[0].max_price == 75000
    assert watches[0].step is None


def test_se_pueden_mezclar_formatos():
    watches = _parse_watchlist("bitcoin:1000,ethereum:2000:4000,solana:5")

    assert len(watches) == 3
    assert watches[0].step == 1000
    assert watches[1].max_price == 4000
    assert watches[2].step == 5


def test_un_lado_vacio():
    watches = _parse_watchlist("ethereum::4000")

    assert watches[0].min_price is None
    assert watches[0].max_price == 4000


def test_ids_a_minusculas_y_sin_espacios():
    watches = _parse_watchlist("  BitCoin:1000  ,  ETHEREUM:100 ")

    assert [w.coin_id for w in watches] == ["bitcoin", "ethereum"]


def test_comas_sobrantes():
    watches = _parse_watchlist("bitcoin:1000,,ethereum:100,")

    assert len(watches) == 2


@pytest.mark.parametrize(
    "entrada",
    [
        "",  # vacia
        "bitcoin",  # sin umbral
        "bitcoin:1000:2000:3000",  # demasiadas partes
        ":1000",  # sin id
        "bitcoin:hola",  # no es un numero
        "bitcoin::",  # ningun umbral
        "bitcoin:0",  # paso cero
        "bitcoin:-100",  # paso negativo
        "bitcoin:75000:55000",  # minimo por encima del maximo
        "bitcoin:60000:60000",  # minimo igual al maximo
    ],
)
def test_entradas_invalidas(entrada):
    with pytest.raises(ConfigError):
        _parse_watchlist(entrada)


# --- porcentaje ---


def test_formato_porcentaje():
    watches = _parse_watchlist("bitcoin:%5")

    assert watches[0].percent == 5
    assert watches[0].step is None
    assert watches[0].min_price is None


def test_porcentaje_con_decimales():
    assert _parse_watchlist("bitcoin:%2.5")[0].percent == 2.5


def test_porcentaje_mezclado_con_los_demas():
    watches = _parse_watchlist("bitcoin:%5,ethereum:100,solana:20:200")

    assert watches[0].percent == 5
    assert watches[1].step == 100
    assert watches[2].max_price == 200


@pytest.mark.parametrize(
    "entrada",
    [
        "bitcoin:%",  # sin numero
        "bitcoin:%0",  # cero
        "bitcoin:%-5",  # negativo
        "bitcoin:%100",  # tendria que doblar
        "bitcoin:%hola",  # no es un numero
    ],
)
def test_porcentajes_invalidos(entrada):
    with pytest.raises(ConfigError):
        _parse_watchlist(entrada)


# --- duraciones ---


def test_duraciones():
    from crypto_tracker.config import parse_duracion

    assert parse_duracion("30m") == 30
    assert parse_duracion("2h") == 120
    assert parse_duracion("1d") == 1440
    assert parse_duracion("1.5h") == 90
    # sin letra se entienden horas
    assert parse_duracion("3") == 180


@pytest.mark.parametrize("entrada", ["", "0h", "-2h", "hola", "2x", "0.001m"])
def test_duraciones_invalidas(entrada):
    from crypto_tracker.config import parse_duracion

    with pytest.raises(ConfigError):
        parse_duracion(entrada)
