"""Tests de /backtest."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.backtest import calcular, interpretar
from crypto_tracker.periodo import PeriodoError

INICIO = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _serie(*precios):
    return [(INICIO + timedelta(days=i), p) for i, p in enumerate(precios)]


def test_sube_baja_y_vuelve_le_gana_a_no_tocar():
    # Vende a 120, recompra a 96 y acaba a 100: tiene más bitcoin que al principio.
    b = calcular(_serie(100, 120, 96, 100), 20)

    assert b.ventas == 1
    assert b.compras == 1
    assert b.dentro
    assert b.final == pytest.approx(1250)
    assert b.hodl == pytest.approx(1000)
    assert b.diferencia == pytest.approx(250)
    assert b.siguiente == pytest.approx(96 * 1.2)


def test_si_sigue_subiendo_te_quedas_fuera():
    b = calcular(_serie(100, 120, 150, 200), 20)

    assert b.ventas == 1
    assert b.compras == 0
    assert not b.dentro
    assert b.final == pytest.approx(1200)
    assert b.hodl == pytest.approx(2000)
    assert b.regla == pytest.approx(20)
    assert b.sin_tocar == pytest.approx(100)
    assert b.siguiente == pytest.approx(96)


def test_sin_moverse_bastante_es_lo_mismo():
    b = calcular(_serie(100, 110, 90, 105), 20)

    assert b.ventas == b.compras == 0
    assert b.final == pytest.approx(b.hodl)


def test_la_referencia_es_la_ultima_operacion_no_el_maximo():
    # Tras vender a 120, sube a 200: recomprar es a 96, no a 160.
    b = calcular(_serie(100, 120, 200, 150), 20)

    assert b.compras == 0


def test_sin_dos_precios():
    assert calcular(_serie(100), 20) is None
    assert calcular([], 20) is None


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("btc", ("bitcoin", 20, 90 * 24)),
        ("btc 15%", ("bitcoin", 15, 90 * 24)),
        ("btc 7,5 30d", ("bitcoin", 7.5, 30 * 24)),
        ("btc +10% 7d", ("bitcoin", 10, 7 * 24)),
        ("", ("", 20, 90 * 24)),
    ],
)
def test_interpretar(texto, sale):
    assert interpretar(texto) == sale


@pytest.mark.parametrize("texto", ["btc x%", "btc 0%", "btc -5%", "btc eth 20%"])
def test_interpretar_mal_escrito(texto):
    with pytest.raises(PeriodoError, match="Escríbelo así"):
        interpretar(texto)


def test_interpretar_100():
    with pytest.raises(PeriodoError, match="menor de 100"):
        interpretar("btc 100%")
