"""Tests de /rebalanceo."""

import pytest

from crypto_tracker.alerts import formatear_rebalanceo
from crypto_tracker.cartera import Valor
from crypto_tracker.rebalanceo import (
    RebalanceoError,
    calcular,
    iguales,
    interpretar,
)

PRECIOS = {"bitcoin": 60000.0, "ethereum": 3000.0, "solana": 150.0}


def _valores(**cuanto):
    return [Valor(c, v, None, v / PRECIOS[c]) for c, v in cuanto.items()]


def test_interpretar():
    assert interpretar("btc 60 eth 40") == {"bitcoin": 60, "ethereum": 40}
    assert interpretar("btc 60%, eth 40%") == {"bitcoin": 60, "ethereum": 40}
    assert interpretar("btc:50 sol:50") == {"bitcoin": 50, "solana": 50}
    assert interpretar("btc 33,3 eth 33,3 sol 33,3") == {
        "bitcoin": 33.3,
        "ethereum": 33.3,
        "solana": 33.3,
    }
    assert interpretar("") is None


@pytest.mark.parametrize(
    "entrada, mensaje",
    [
        ("btc 60 eth", "Cada cripto con su %"),
        ("btc mucho eth 40", "No entiendo 'mucho'"),
        ("btc -10 eth 110", "No entiendo '-10'"),
        ("btc 50 bitcoin 50", "dos veces"),
        ("btc 60 eth 30", "suma 90%"),
        ("btc 70 eth 40,5", "suma 110,5%"),
    ],
)
def test_interpretar_mal(entrada, mensaje):
    with pytest.raises(RebalanceoError, match=mensaje):
        interpretar(entrada)


def test_iguales():
    assert iguales(["bitcoin", "ethereum"]) == {"bitcoin": 50, "ethereum": 50}


def test_calcular_vende_y_compra():
    pasos = calcular(
        _valores(bitcoin=7000, ethereum=3000),
        {"bitcoin": 60, "ethereum": 40},
        PRECIOS,
    )

    btc, eth = pasos
    assert btc.coin_id == "bitcoin"
    assert btc.mover == pytest.approx(-1000)
    assert btc.cantidad == pytest.approx(1000 / 60000)
    assert btc.peso == pytest.approx(70)
    assert eth.mover == pytest.approx(1000)
    assert eth.cantidad == pytest.approx(1000 / 3000)


def test_la_que_no_nombras_se_vende_entera():
    pasos = calcular(_valores(bitcoin=5000, solana=5000), {"bitcoin": 100}, PRECIOS)

    sol = next(p for p in pasos if p.coin_id == "solana")
    assert sol.mover == -5000
    assert sol.cantidad == pytest.approx(5000 / 150)
    assert sol.objetivo == 0


def test_una_nueva_se_compra():
    pasos = calcular(_valores(bitcoin=10000), {"bitcoin": 80, "solana": 20}, PRECIOS)

    sol = next(p for p in pasos if p.coin_id == "solana")
    assert sol.ahora == 0
    assert sol.peso == 0
    assert sol.mover == pytest.approx(2000)


def test_lo_que_casi_esta_no_se_mueve():
    pasos = calcular(
        _valores(bitcoin=5050, ethereum=4950),
        {"bitcoin": 50, "ethereum": 50},
        PRECIOS,
    )

    assert [p.mover for p in pasos] == [0, 0]


def test_orden_primero_ventas_luego_compras_luego_quietas():
    pasos = calcular(
        _valores(bitcoin=5000, ethereum=3000, solana=2000),
        {"bitcoin": 30, "ethereum": 30, "solana": 40},
        PRECIOS,
    )

    assert [p.coin_id for p in pasos] == ["bitcoin", "solana", "ethereum"]


def test_cartera_sin_valor():
    assert calcular([], {"bitcoin": 100}, PRECIOS) == []


def test_formatear():
    pasos = calcular(
        _valores(bitcoin=7000, ethereum=2000, solana=1000),
        {"bitcoin": 60, "ethereum": 30, "solana": 10},
        PRECIOS,
    )
    texto = formatear_rebalanceo(pasos, 10000, "eur", iguales=False)

    assert "⚖️ <b>Para dejar tu cartera en tu reparto</b>" in texto
    assert "€10.000,00" in texto
    assert "💸 Vende <b>€1.000,00</b> de Bitcoin (0,01666667)" in texto
    assert "70% → 60%" in texto
    assert "🛒 Compra <b>€1.000,00</b> de Ethereum (0,33333333)" in texto
    assert "✅ Solana ya está bien: 10%" in texto
    assert "comisiones" in texto
    assert "partes iguales" not in texto


def test_formatear_a_partes_iguales():
    pasos = calcular(
        _valores(bitcoin=6000, ethereum=4000), iguales(["bitcoin", "ethereum"]), PRECIOS
    )
    texto = formatear_rebalanceo(pasos, 10000, "eur", iguales=True)

    assert "a partes iguales" in texto
    assert "/rebalanceo btc 60 eth 40" in texto


def test_formatear_todo_en_su_sitio():
    pasos = calcular(_valores(bitcoin=10000), {"bitcoin": 100}, PRECIOS)
    texto = formatear_rebalanceo(pasos, 10000, "eur", iguales=False)

    assert "Ya la tienes así, no hay nada que mover" in texto


def test_formatear_vender_todo():
    pasos = calcular(_valores(bitcoin=5000, solana=5000), {"bitcoin": 100}, PRECIOS)
    texto = formatear_rebalanceo(pasos, 10000, "eur", iguales=False)

    assert "Vende toda la de Solana" in texto
