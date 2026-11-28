"""Tests de lo que te has perdido mientras callaba."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.avisos.perdido import calcular, movida

DESDE = datetime(2026, 11, 16, 8, tzinfo=timezone.utc)


def _serie(*precios):
    return [(DESDE + timedelta(minutes=10 * i), p) for i, p in enumerate(precios)]


def test_movida():
    m = movida("bitcoin", _serie(100, 130, 90, 110))

    assert (m.antes, m.ahora, m.maximo, m.minimo) == (100, 110, 130, 90)
    assert m.cambio == pytest.approx(10)


def test_movida_sin_dos_precios():
    assert movida("bitcoin", _serie(100)) is None
    assert movida("bitcoin", []) is None


def test_de_la_que_mas_se_mueve_a_la_que_menos():
    p = calcular(
        DESDE,
        DESDE + timedelta(hours=3),
        {
            "bitcoin": _serie(100, 102),
            "solana": _serie(100, 90),
            "ethereum": _serie(100, 105),
            "nueva": _serie(5),
        },
        _serie(1000, 1030),
    )

    assert [m.coin_id for m in p.movidas] == ["solana", "ethereum", "bitcoin"]
    assert p.cartera == pytest.approx(3)
    assert p.tiempo == timedelta(hours=3)


def test_sin_cartera():
    assert calcular(DESDE, DESDE, {}, []).cartera is None
