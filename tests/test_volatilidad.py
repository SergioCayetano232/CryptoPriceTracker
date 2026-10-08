"""Tests de /volatilidad."""

from datetime import date, datetime, timedelta, timezone

import pytest

from crypto_tracker.periodo import PeriodoError
from crypto_tracker.volatilidad import (
    Volatilidad,
    avisos,
    calcular,
    interpretar,
    por_dias,
)

# A mediodia: asi la hora de aqui no cambia el dia.
INICIO = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def _diaria(*precios):
    return [(INICIO + timedelta(days=i), p) for i, p in enumerate(precios)]


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("bitcoin 7d", ("bitcoin", 168)),
        ("btc", ("bitcoin", 720)),
        ("7d", ("", 168)),
        ("", ("", 720)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


@pytest.mark.parametrize("argumento", ["bitcoin 12h", "bitcoin 1d", "btc eth 7d"])
def test_interpretar_malo(argumento):
    with pytest.raises(PeriodoError):
        interpretar(argumento)


def test_por_dias_se_queda_con_el_ultimo():
    serie = [
        (INICIO, 100.0),
        (INICIO + timedelta(hours=3), 105.0),
        (INICIO + timedelta(days=1), 110.0),
    ]

    assert [p for _, p in por_dias(serie)] == [105.0, 110.0]


def test_calcular():
    # +8%, -10%, +5%: de media un 7,67% al dia, el peor el -10%
    resultado = calcular(_diaria(100, 108, 97.2, 102.06))

    assert resultado == Volatilidad(
        pytest.approx(7.667, 0.001), pytest.approx(-10), date(2026, 10, 3), 3
    )


def test_calcular_salta_los_huecos():
    serie = _diaria(100, 102) + [(INICIO + timedelta(days=10), 200.0)]

    resultado = calcular(serie)

    assert resultado.dias == 1
    assert resultado.media == pytest.approx(2)


def test_calcular_con_un_solo_dia():
    assert calcular(_diaria(100)) is None
    assert calcular([]) is None


def test_avisos():
    serie = _diaria(100, 103, 106, 101, 100)

    # El primero solo anota. Con %2: 103, 106 y 101 avisan; 100 no (-0,99%).
    assert avisos(serie, 2) == 3
    assert avisos(serie, 5) == 2  # 106 desde 100, y 100 desde 106
    assert avisos(serie, 10) == 0
