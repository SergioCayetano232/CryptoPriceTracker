"""Tests de /copia."""

from datetime import time

import pytest

from crypto_tracker.alerts import formatear_copia
from crypto_tracker.config import (
    Posicion,
    Watch,
    _parse_watchlist,
    parse_cartera,
    parse_hora,
)
from crypto_tracker.copia import lineas, numero, posicion, regla

VIGILADAS = [
    Watch("bitcoin", percent=5),
    Watch("solana", step=10),
    Watch("ethereum", min_price=2000.5, max_price=4000),
    Watch("ripple", max_price=3),
    Watch("dogecoin", min_price=0.12345678),
]
CARTERA = (Posicion("bitcoin", 0.016, 1000), Posicion("solana", 3))


@pytest.mark.parametrize(
    "valor,esperado",
    [(75000, "75000"), (0.016, "0.016"), (2.5, "2.5"), (0.00000123, "0.00000123")],
)
def test_numero(valor, esperado):
    assert numero(valor) == esperado


def test_regla():
    assert [regla(w) for w in VIGILADAS] == [
        "bitcoin:%5",
        "solana:10",
        "ethereum:2000.5:4000",
        "ripple::3",
        "dogecoin:0.12345678:",
    ]


def test_posicion():
    assert [posicion(p) for p in CARTERA] == ["bitcoin:0.016:1000", "solana:3"]


def test_lineas_se_leen_igual_desde_el_env():
    watch, cartera, resumen = lineas(VIGILADAS, CARTERA, time(8, 30))

    assert _parse_watchlist(watch.removeprefix("WATCHLIST=")) == VIGILADAS
    assert parse_cartera(cartera.removeprefix("PORTFOLIO=")) == CARTERA
    assert parse_hora(resumen.removeprefix("RESUMEN_DIARIO=")) == time(8, 30)


def test_lineas_vacias():
    assert lineas([], (), None)[1:] == ["PORTFOLIO=", "RESUMEN_DIARIO="]


def test_formatear():
    texto = formatear_copia(["WATCHLIST=bitcoin:%5", "PORTFOLIO=", "RESUMEN_DIARIO="])

    assert "<code>WATCHLIST=bitcoin:%5\nPORTFOLIO=\nRESUMEN_DIARIO=</code>" in texto
    assert "Telegram" in texto
