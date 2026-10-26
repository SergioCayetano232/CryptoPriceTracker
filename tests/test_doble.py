"""Tests de /doble."""

import pytest

from crypto_tracker.alerts import formatear_doble
from crypto_tracker.cartera import Valor
from crypto_tracker.doble import Cartera, Doble, calcular


def test_cuanto_le_falta_a_cada_una():
    valores = [
        Valor("bitcoin", 2240.0, 1000.0, 0.016),  # a 140.000, le salió a 62.500
        Valor("solana", 750.0, 1000.0, 5.0),  # a 150, le salió a 200
    ]

    c = calcular(valores)

    assert [d.coin_id for d in c.criptos] == ["solana", "bitcoin"]
    assert c.criptos[0].objetivo == pytest.approx(400)
    assert c.criptos[0].falta == pytest.approx(166.667, abs=0.001)
    assert c.criptos[1].objetivo == pytest.approx(125000)
    assert c.criptos[1].falta == pytest.approx(-10.714, abs=0.001)
    assert c.total == pytest.approx((4000 / 2990 - 1) * 100)
    assert c.sin_coste == []


def test_sin_coste_no_hay_total():
    valores = [Valor("bitcoin", 1120.0, 1000.0, 0.016), Valor("eth", 900.0, None, 0.4)]

    c = calcular(valores)

    assert [d.coin_id for d in c.criptos] == ["bitcoin"]
    assert c.total is None
    assert c.sin_coste == ["eth"]


def test_formatear():
    c = Cartera(
        [Doble("solana", 150.0, 200.0), Doble("bitcoin", 140000.0, 62500.0)],
        33.78,
        ["ethereum"],
    )

    texto = formatear_doble(c, "eur")

    assert texto.startswith("✌️ <b>Para doblar lo que metiste</b>\n\n")
    assert (
        "🔴 <b>Solana</b> a €400,00 · falta <b>+166.67%</b>\n"
        "   <i>ahora €150,00, te salió a €200,00</i>"
    ) in texto
    assert "🟢 <b>Bitcoin</b> a €125.000,00 · ya lo has doblado" in texto
    assert "Todo junto tendría que subir un <b>+33.78%</b>" in texto
    assert "De Ethereum no sé lo que te costó." in texto


def test_formatear_todo_doblado():
    c = Cartera([Doble("bitcoin", 140000.0, 62500.0)], -10.71, [])

    texto = formatear_doble(c, "eur")

    assert "Todo junto ya lo has doblado 🎉" in texto
    assert "no sé" not in texto
