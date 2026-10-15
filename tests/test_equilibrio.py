"""Tests de /equilibrio."""

import pytest

from crypto_tracker.alerts import formatear_equilibrio
from crypto_tracker.cartera import Valor
from crypto_tracker.equilibrio import Cartera, Equilibrio, calcular


def test_cuanto_le_falta_a_cada_una():
    valores = [
        Valor("bitcoin", 1120.0, 1000.0, 0.016),  # a 70.000, le salió a 62.500
        Valor("solana", 750.0, 1000.0, 5.0),  # a 150, le salió a 200
    ]

    c = calcular(valores)

    assert [e.coin_id for e in c.criptos] == ["solana", "bitcoin"]
    assert c.criptos[0].medio == pytest.approx(200)
    assert c.criptos[0].falta == pytest.approx(33.333, abs=0.001)
    assert c.criptos[1].falta == pytest.approx(-10.714, abs=0.001)
    assert c.total == pytest.approx((2000 / 1870 - 1) * 100)
    assert c.sin_coste == []


def test_sin_coste_no_hay_total():
    valores = [Valor("bitcoin", 1120.0, 1000.0, 0.016), Valor("eth", 900.0, None, 0.4)]

    c = calcular(valores)

    assert [e.coin_id for e in c.criptos] == ["bitcoin"]
    assert c.total is None
    assert c.sin_coste == ["eth"]


def test_formatear():
    c = Cartera(
        [
            Equilibrio("solana", 150.0, 200.0),
            Equilibrio("bitcoin", 70000.0, 62500.0),
        ],
        6.95,
        ["ethereum"],
    )

    texto = formatear_equilibrio(c, "eur")

    assert texto.startswith("🧮 <b>Para no perder</b>\n\n")
    assert (
        "🔴 <b>Solana</b> a €200,00 · falta <b>+33.33%</b>\n   <i>ahora €150,00</i>"
        in texto
    )
    assert "🟢 <b>Bitcoin</b> a €62.500,00 · ya ganas, aguanta <b>-10.71%</b>" in texto
    assert "📦 Todo junto tendría que subir un <b>+6.95%</b>" in texto
    assert "De Ethereum no sé lo que te costó." in texto


def test_formatear_todo_en_ganancias():
    c = Cartera([Equilibrio("bitcoin", 70000.0, 62500.0)], -10.71, [])

    texto = formatear_equilibrio(c, "eur")

    assert "Todo junto vas ganando: aguanta una bajada del <b>10.71%</b>" in texto
    assert "no sé lo que te costó" not in texto
