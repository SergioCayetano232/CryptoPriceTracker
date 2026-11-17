"""Tests de /pienso."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.pienso import (
    Pienso,
    PiensoError,
    a_texto,
    comando_compra,
    de_texto,
    interpretar,
    tocan,
)

AHORA = datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("btc 500", ("bitcoin", 500)),
        ("eth 1.500", ("ethereum", 1500)),
        ("sol 50,5", ("solana", 50.5)),
        ("btc no", ("bitcoin", None)),
        ("btc quitar", ("bitcoin", None)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


@pytest.mark.parametrize("argumento", ["", "btc", "btc mucho", "btc -5", "btc 0"])
def test_interpretar_malo(argumento):
    with pytest.raises(PiensoError):
        interpretar(argumento)


def test_tocan_a_las_24_h():
    p = Pienso("bitcoin", 500, 60000, AHORA)

    assert tocan([p], AHORA + timedelta(hours=23, minutes=59)) == []
    assert tocan([p], AHORA + timedelta(hours=24)) == [p]


def test_cambio():
    p = Pienso("bitcoin", 500, 60000, AHORA)

    assert p.cambio(57000) == pytest.approx(-5)


def test_comando_compra():
    p = Pienso("bitcoin", 500, 60000, AHORA)

    assert comando_compra(p, 64000) == "/compra bitcoin 0,0078125 500"


def test_comando_compra_cabe_en_un_boton():
    p = Pienso("matic-network", 1234.5, 0.5, AHORA)

    assert len(comando_compra(p, 0.123456).encode()) <= 64


def test_a_texto_y_vuelta():
    p = Pienso("bitcoin", 500.5, 60123.45, AHORA)

    assert de_texto("bitcoin", a_texto(p)) == p


@pytest.mark.parametrize("texto", ["", "basura", "x|1|2", "2026-11-17T10:00:00|a|b"])
def test_de_texto_malo(texto):
    assert de_texto("bitcoin", texto) is None
