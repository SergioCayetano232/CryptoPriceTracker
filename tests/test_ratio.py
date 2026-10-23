"""Tests de /ratio."""

from datetime import date, timedelta

import pytest

from crypto_tracker.alerts import formatear_ratio
from crypto_tracker.periodo import PeriodoError
from crypto_tracker.ratio import Ratio, calcular, interpretar

HOY = date(2026, 10, 14)


def _dias(*precios):
    """Un precio por día, el último es hoy."""
    return [
        (HOY - timedelta(days=len(precios) - 1 - i), p) for i, p in enumerate(precios)
    ]


def test_lo_que_vale_una_en_otra():
    r = calcular(_dias(3000.0, 3300.0), _dias(100000.0, 100000.0))

    assert r.antes == pytest.approx(0.03)
    assert r.ahora == pytest.approx(0.033)
    assert r.cambio == pytest.approx(10)
    assert r.desde == HOY - timedelta(days=1)


def test_solo_los_dias_que_tienen_las_dos():
    una = _dias(10.0, 20.0, 30.0)
    otra = [(HOY - timedelta(days=2), 10.0), (HOY, 10.0)]

    r = calcular(una, otra)

    assert [v for _, v in r.dias] == [1.0, 3.0]


def test_sin_dos_dias_en_comun():
    assert calcular([], []) is None
    assert calcular(_dias(10.0, 20.0), [(HOY, 5.0)]) is None
    assert calcular(_dias(10.0, 20.0), _dias(0.0, 0.0)) is None


def test_interpretar():
    assert interpretar("eth btc 7d") == (["ethereum", "bitcoin"], 7 * 24)
    assert interpretar("eth btc") == (["ethereum", "bitcoin"], 30 * 24)
    assert interpretar("") == ([], 30 * 24)
    with pytest.raises(PeriodoError, match="De dos en dos"):
        interpretar("eth")
    with pytest.raises(PeriodoError, match="misma"):
        interpretar("btc bitcoin")


def test_formatear():
    r = Ratio(_dias(0.030, 0.031, 0.029, 0.030, 0.032, 0.033))

    texto = formatear_ratio("ethereum", "bitcoin", r, 30 * 24)

    assert texto.startswith("⚖️ <b>Ethereum</b> en <b>Bitcoin</b>, últimos 30 días")
    assert "1 Ethereum = <b>0,0330</b> Bitcoin\n" in texto
    assert "🔺 +10.00% desde el 09/10 (0,0300)\n" in texto
    assert "<code>" in texto
    assert "Máximo 0,0330 · Mínimo 0,0290" in texto


def test_formatear_pocos_dias_sin_barritas():
    texto = formatear_ratio("bitcoin", "ethereum", Ratio(_dias(33.0, 30.0)), 7 * 24)

    assert texto.count("<code>") == 1  # solo la del rango
    assert "🔻 -9.09%" in texto


def test_posicion_en_el_rango():
    r = Ratio(_dias(0.030, 0.034, 0.029, 0.032))

    assert r.maximo == 0.034
    assert r.minimo == 0.029
    assert r.posicion == pytest.approx(60)
    assert Ratio(_dias(0.03, 0.03)).posicion is None


def test_formatear_con_la_barra_del_rango():
    texto = formatear_ratio(
        "ethereum", "bitcoin", Ratio(_dias(0.030, 0.034, 0.029, 0.032)), 30 * 24
    )

    assert "<code>mín ━━━━━●━━━━ máx</code> al 60% del rango\n" in texto


def test_formatear_sin_moverse_no_hay_barra():
    texto = formatear_ratio("ethereum", "bitcoin", Ratio(_dias(0.03, 0.03)), 7 * 24)

    assert "del rango" not in texto
