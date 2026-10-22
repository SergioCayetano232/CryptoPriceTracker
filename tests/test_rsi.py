"""Tests de /rsi."""

from datetime import date, timedelta

import pytest

from crypto_tracker.alerts import formatear_rsi
from crypto_tracker.rsi import Rsi, calcular, hasta_zona

HOY = date(2026, 10, 12)

# El ejemplo de Wilder que copia todo el mundo (StockCharts): sale 70,53.
WILDER = [
    44.3389, 44.0902, 44.1497, 43.6124, 44.2779, 44.8264, 45.0955, 45.4245,
    45.8433, 46.0826, 45.8931, 46.0328, 45.614, 46.282, 46.282,
]  # fmt: skip


def _dias(*precios):
    """Un precio por día, el último es hoy."""
    return [
        (HOY - timedelta(days=len(precios) - 1 - i), p) for i, p in enumerate(precios)
    ]


def test_calcular_como_wilder():
    r = calcular(_dias(*WILDER))

    assert r.valor == pytest.approx(70.53, abs=0.01)
    assert (r.ahora, r.dias) == (46.282, 15)


def test_calcular_suaviza_los_dias_siguientes():
    assert calcular(_dias(*WILDER, 46.0028)).valor == pytest.approx(66.32, abs=0.01)
    assert calcular(_dias(*WILDER, 46.0028, 46.0328)).valor == pytest.approx(
        66.55, abs=0.01
    )


def test_calcular_sin_bajadas_ni_subidas():
    assert calcular(_dias(*range(100, 115))).valor == 100
    assert calcular(_dias(*range(115, 100, -1))).valor == 0
    assert calcular(_dias(*[100] * 15)).valor == 50


def test_calcular_con_pocos_dias():
    assert calcular(_dias(*WILDER[:-1])) is None
    assert calcular([]) is None


def test_calcular_solo_lo_que_va_despues_de_un_hueco():
    viejo = [(HOY - timedelta(days=40), 10.0)]

    r = calcular(viejo + _dias(*WILDER))

    assert r.dias == 15  # el de hace 40 días no cuenta
    assert calcular(viejo + _dias(*WILDER[1:])) is None


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (75, "🔥 <b>Sobrecomprada</b>"),
        (25, "🧊 <b>Sobrevendida</b>"),
        (50, "😐 <b>Neutral</b>"),
    ],
)
def test_formatear(valor, esperado):
    texto = formatear_rsi("bitcoin", Rsi(valor, 110, 90), "eur")

    assert f"📊 <b>Bitcoin</b>, RSI de 14 días: <b>{valor}</b>" in texto
    assert esperado in texto
    assert "Ahora €110,00" in texto


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (62, (8, True)),
        (50, (20, True)),
        (41, (11, False)),
        (70, None),
        (25, None),
    ],
)
def test_hasta_zona(valor, esperado):
    assert hasta_zona(valor) == esperado


def test_formatear_neutral_dice_cuanto_falta():
    texto = formatear_rsi("bitcoin", Rsi(62, 110, 90), "eur")

    assert "Le faltan 8 puntos para sobrecomprada" in texto
    assert "menos de 1" in formatear_rsi("bitcoin", Rsi(69.6, 110, 90), "eur")
    assert "Le faltan" not in formatear_rsi("bitcoin", Rsi(75, 110, 90), "eur")


def test_formatear_con_pocos_dias_lo_avisa():
    texto = formatear_rsi("bitcoin", Rsi(60, 110, 20), "eur")

    assert "Con solo 20 días" in texto
