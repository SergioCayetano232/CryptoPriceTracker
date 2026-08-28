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
