"""Tests de /spread."""

import pytest

from crypto_tracker.indicadores.spread import (
    Fila,
    SpreadError,
    calcular,
    interpretar,
    por_que_no,
    texto,
)
from crypto_tracker.nucleo.simbolos import MAX_VARIAS


def test_interpretar():
    assert interpretar("btc, eth btc") == ["bitcoin", "ethereum"]
    assert interpretar("") == []
    with pytest.raises(SpreadError):
        interpretar(" ".join(f"c{i}" for i in range(MAX_VARIAS + 1)))


def test_diferencia():
    assert Fila("bitcoin", 100, 101).diferencia == pytest.approx(1)
    assert Fila("bitcoin", 100, 98).diferencia == pytest.approx(-2)


def test_calcular_ordena_por_lo_separadas():
    filas, sueltas = calcular(
        ["bitcoin", "ethereum", "tether", "pepe"],
        {"bitcoin": 100, "ethereum": 100, "tether": 1, "pepe": 0.1},
        {"bitcoin": 100.1, "ethereum": 95},
    )

    assert [f.coin_id for f in filas] == ["ethereum", "bitcoin"]
    assert sueltas == ["tether", "pepe"]


def test_por_que_no():
    assert "estable" in por_que_no("tether")
    assert "no sé cómo se llama" in por_que_no("pepe")
    assert "ahora mismo" in por_que_no("bitcoin")


def test_texto():
    t = texto(
        [
            Fila("ethereum", 2000, 1900),
            Fila("bitcoin", 60000, 60060),
            Fila("solana", 100, 100.01),
        ],
        ["tether"],
        "eur",
    )

    assert "⚠️ <b>Ethereum</b>  €2.000,00 · €1.900,00  <i>(-5,00%)</i>" in t
    assert "✅ <b>Bitcoin</b>  €60.000,00 · €60.060,00  <i>(+0,10%)</i>" in t
    assert "✅ <b>Solana</b>  €100,00 · €100,01  <i>(igual)</i>" in t
    assert "suele ser un dato malo" in t
    assert "➖ <b>Tether</b>: es una estable" in t
    assert "EUR/USDT" in t
    assert t.index("Tether") < t.index("dato malo")


def test_texto_sin_nada_raro_ni_euros():
    t = texto([Fila("bitcoin", 60000, 60060)], [], "usd")

    assert "dato malo" not in t
    assert "EUR/USDT" not in t
    assert "no vale justo un dólar" in t
    assert "$60.000,00" in t
