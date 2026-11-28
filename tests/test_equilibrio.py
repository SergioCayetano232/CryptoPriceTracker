"""Tests de /equilibrio."""

import pytest

from crypto_tracker.avisos.alerts import formatear_equilibrio, formatear_vuelta
from crypto_tracker.cartera import Valor
from crypto_tracker.equilibrio import Cartera, Equilibrio, calcular, vuelta


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


# --- el aviso de que vuelve a lo que costó ---


@pytest.mark.parametrize(
    "precio, esperando, sale",
    [
        (96.0, False, (False, False)),  # pierde un 4%: todavía no cuenta
        (95.0, False, (False, True)),  # pierde un 5%: ya espera
        (99.0, True, (False, True)),  # recuperando, sin llegar
        (100.0, True, (True, False)),  # llega: aviso, y deja de esperar
        (130.0, True, (True, False)),  # se pasó entre ciclo y ciclo, vale igual
        (110.0, False, (False, False)),  # ganando sin haber perdido: nada
    ],
)
def test_vuelta(precio, esperando, sale):
    assert vuelta(Equilibrio("solana", precio, 100.0), esperando) == sale


def test_formatear_vuelta():
    texto = formatear_vuelta(Equilibrio("solana", 201.5, 200.0), "eur")

    assert "<b>Solana</b> vuelve a lo que te costó, €200,00" in texto
    assert "<b>€201,50</b>" in texto
