"""Tests de /ath."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.maximo import Maximo, hace, leer

FECHA = datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc)


def _dato(**cambios):
    dato = {
        "id": "bitcoin",
        "current_price": 75000.0,
        "ath": 100000.0,
        "ath_date": "2026-03-14T10:00:00.000Z",
    }
    return {**dato, **cambios}


def test_leer():
    assert leer([_dato()]) == {"bitcoin": Maximo("bitcoin", 75000, 100000, FECHA)}


@pytest.mark.parametrize(
    "raro",
    [
        {"ath": None},
        {"ath": 0},
        {"current_price": 0},
        {"ath_date": "ayer"},
        {"ath_date": None},
        {"id": None, "ath": "mucho"},
    ],
)
def test_leer_ignora_lo_raro(raro):
    assert leer([_dato(**raro), _dato(id="solana")]).keys() == {"solana"}


def test_leer_algo_que_no_es_lista():
    assert leer({"error": "no"}) == {}


def test_falta():
    assert Maximo("bitcoin", 75000, 100000, FECHA).falta() == pytest.approx(33.33, 0.01)
    assert Maximo("bitcoin", 100000, 100000, FECHA).falta() == 0
    # CoinGecko a veces va un ciclo por detras y el precio supera al maximo.
    assert Maximo("bitcoin", 101000, 100000, FECHA).falta() == 0


@pytest.mark.parametrize(
    "dias,esperado",
    [
        (0, "hoy"),
        (1, "ayer"),
        (12, "hace 12 días"),
        (59, "hace 59 días"),
        (210, "hace 7 meses"),
        (364, "hace 12 meses"),
        (400, "hace 1 año"),
        (3 * 365 + 10, "hace 3 años"),
    ],
)
def test_hace(dias, esperado):
    assert hace(FECHA, FECHA + timedelta(days=dias, hours=3)) == esperado
