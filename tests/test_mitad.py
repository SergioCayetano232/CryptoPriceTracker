"""Tests de /mitad."""

import pytest

from crypto_tracker.alerts import formatear_mitad
from crypto_tracker.cartera import Valor
from crypto_tracker.mitad import Cartera, Mitad, calcular


def test_cuanto_aguanta_cada_una():
    valores = [
        Valor("bitcoin", 2240.0, 1000.0, 0.016),  # a 140.000, le salió a 62.500
        Valor("solana", 750.0, 1000.0, 5.0),  # a 150, le salió a 200
    ]

    c = calcular(valores)

    # La que menos aguanta, primero
    assert [m.coin_id for m in c.criptos] == ["solana", "bitcoin"]
    assert c.criptos[0].objetivo == pytest.approx(100)
    assert c.criptos[0].aguanta == pytest.approx(33.333, abs=0.001)
    assert c.criptos[1].objetivo == pytest.approx(31250)
    assert c.criptos[1].aguanta == pytest.approx(77.679, abs=0.001)
    assert c.total == pytest.approx((1 - 1000 / 2990) * 100)
    assert c.sin_coste == []


def test_ya_por_debajo():
    m = Mitad("solana", 80.0, 200.0)

    assert m.aguanta == pytest.approx(-25)


def test_sin_coste_no_hay_total():
    valores = [Valor("bitcoin", 1120.0, 1000.0, 0.016), Valor("eth", 900.0, None, 0.4)]

    c = calcular(valores)

    assert [m.coin_id for m in c.criptos] == ["bitcoin"]
    assert c.total is None
    assert c.sin_coste == ["eth"]


def test_formatear():
    c = Cartera(
        [Mitad("solana", 80.0, 200.0), Mitad("bitcoin", 140000.0, 62500.0)],
        66.56,
        ["ethereum"],
    )

    texto = formatear_mitad(c, "eur")

    assert texto.startswith("🪓 <b>Para perder la mitad de lo que metiste</b>\n\n")
    assert "🔴 <b>Solana</b> a €100,00 · ya está por debajo" in texto
    assert (
        "🟢 <b>Bitcoin</b> a €31.250,00 · aguanta <b>-77.68%</b>\n"
        "   <i>ahora €140.000,00, te salió a €62.500,00</i>"
    ) in texto
    assert "Todo junto aguanta una bajada del <b>66.56%</b>" in texto
    assert "De Ethereum no sé lo que te costó." in texto


def test_formatear_todo_por_debajo():
    c = Cartera([Mitad("solana", 80.0, 200.0)], -25.0, [])

    texto = formatear_mitad(c, "eur")

    assert "Todo junto ya vale menos de la mitad de lo que metiste" in texto
    assert "no sé" not in texto
