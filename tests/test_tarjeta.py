"""Tests de /tarjeta."""

from datetime import date, datetime, timedelta, timezone

import pytest

from crypto_tracker.cartera import Valor
from crypto_tracker.periodo import PeriodoError
from crypto_tracker.tarjeta import calcular, interpretar, reducir

HOY = date(2026, 11, 16)
INICIO = datetime(2026, 10, 17, tzinfo=timezone.utc)
VALORES = [
    Valor("bitcoin", 7500, 5000, 0.1),
    Valor("solana", 2500, 1000, 10),
]


def _serie(*valores):
    return [(INICIO + timedelta(days=i), v) for i, v in enumerate(valores)]


def test_solo_porcentajes():
    t = calcular(VALORES, _serie(8000, 9000, 10000), 30 * 24, HOY)

    assert t.total == pytest.approx(66.67, abs=0.01)  # 10.000 sobre 6.000
    assert t.tramo == pytest.approx(25)
    assert t.linea == pytest.approx([0, 12.5, 25])
    assert [(r.coin_id, r.peso) for r in t.reparto] == [
        ("bitcoin", 75),
        ("solana", 25),
    ]


def test_sin_saber_lo_que_costo():
    valores = [Valor("bitcoin", 7500, None, 0.1)]

    t = calcular(valores, _serie(8000, 7500), 30 * 24, HOY)

    assert t.total is None
    assert t.tramo == pytest.approx(-6.25)


def test_sin_precios_guardados():
    t = calcular(VALORES, _serie(8000), 30 * 24, HOY)

    assert t.tramo is None
    assert t.linea == []


def test_sin_valor_no_hay_tarjeta():
    assert calcular([Valor("bitcoin", 0, 100, 0)], [], 24, HOY) is None
    assert calcular([], [], 24, HOY) is None


def test_reducir():
    valores = list(range(1001))

    sale = reducir(valores, 11)

    assert sale == [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    assert reducir([1, 2, 3], 11) == [1, 2, 3]


@pytest.mark.parametrize("texto, sale", [("", 720), ("90d", 2160), ("7d", 168)])
def test_interpretar(texto, sale):
    assert interpretar(texto) == sale


def test_interpretar_mal_escrito():
    with pytest.raises(PeriodoError, match="Escríbelo así"):
        interpretar("bitcoin")
