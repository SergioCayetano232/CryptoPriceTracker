"""Tests de /quieta."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.alerts import formatear_quieta
from crypto_tracker.quieta import Quieta, calcular

T = datetime(2026, 11, 3, tzinfo=timezone.utc)


def _serie(*precios):
    return [(T, p) for p in precios]


def test_de_la_mas_quieta_a_la_que_mas_se_mueve():
    series = {
        "solana": _serie(100, 110, 100),
        "bitcoin": _serie(100, 102),
        "ethereum": _serie(100, 95, 100),
    }

    quietas = calcular(series)

    assert [q.coin_id for q in quietas] == ["bitcoin", "ethereum", "solana"]
    assert quietas[0].rango == pytest.approx(2)
    assert quietas[2].rango == pytest.approx(10)


def test_con_un_solo_precio_no_cuenta():
    assert calcular({"bitcoin": _serie(100), "solana": []}) == []


def test_formatear():
    texto = formatear_quieta(
        [Quieta("bitcoin", 100.0, 101.5), Quieta("usd-coin", 0.99, 1.1)], "eur"
    )

    assert texto.startswith("😴 <b>La más quieta en 24 h: Bitcoin</b>\n")
    assert "Se ha movido entre €100,00 y €101,50, un <b>1.50%</b>" in texto
    assert "· Usd Coin  11.11%" in texto


def test_formatear_una_sola():
    texto = formatear_quieta([Quieta("bitcoin", 100.0, 101.0)], "eur")

    assert "·" not in texto
