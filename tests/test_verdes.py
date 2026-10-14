"""Tests de /verdes."""

from datetime import date, timedelta

import pytest

from crypto_tracker.alerts import formatear_verdes
from crypto_tracker.periodo import PeriodoError
from crypto_tracker.verdes import Verdes, calcular, interpretar

HOY = date(2026, 10, 14)


def _dias(*precios):
    """Un precio por día, el último es hoy."""
    return [
        (HOY - timedelta(days=len(precios) - 1 - i), p) for i, p in enumerate(precios)
    ]


def test_cuenta_los_que_suben_y_bajan():
    v = calcular(_dias(100, 105, 103, 110, 110, 108))

    assert (v.suben, v.bajan, v.iguales) == (2, 2, 1)
    assert v.total == 5
    assert v.porcentaje == pytest.approx(40)
    assert v.desde == HOY - timedelta(days=5)


def test_salta_los_huecos():
    dias = [(HOY - timedelta(days=10), 50.0), *_dias(100, 105)]

    v = calcular(dias)

    assert (v.suben, v.bajan) == (1, 0)  # de 50 a 100 no cuenta
    assert v.desde == HOY - timedelta(days=1)


def test_sin_dos_dias_seguidos():
    assert calcular([]) is None
    assert calcular(_dias(100)) is None
    assert calcular([(HOY - timedelta(days=3), 100.0), (HOY, 110.0)]) is None


def test_interpretar():
    assert interpretar("btc 7d") == ("bitcoin", 7 * 24)
    assert interpretar("solana") == ("solana", 30 * 24)
    assert interpretar("14d") == ("", 14 * 24)
    assert interpretar("") == ("", 30 * 24)
    with pytest.raises(PeriodoError):
        interpretar("btc eth 7d")


def test_formatear():
    texto = formatear_verdes("bitcoin", Verdes(18, 12, 0, HOY), 30 * 24)

    assert "🟢 <b>Bitcoin</b>, últimos 30 días" in texto
    assert "<b>18</b> en verde y <b>12</b> en rojo\n" in texto
    assert "🟩🟩🟩🟩🟩🟩🟥🟥🟥🟥 sube el <b>60%</b> de los días" in texto
    assert "Solo tengo" not in texto


def test_formatear_mas_rojos_con_iguales_e_incompleto():
    v = Verdes(2, 5, 1, HOY - timedelta(days=8))

    texto = formatear_verdes("solana", v, 30 * 24, incompleto=True)

    assert texto.startswith("🔴")
    assert "en rojo (1 sin cambios)" in texto
    assert "sube el <b>25%</b>" in texto
    assert "Solo tengo precios desde el 06/10." in texto


def test_formatear_empate():
    assert formatear_verdes("eth", Verdes(3, 3, 0, HOY), 7 * 24).startswith("⚪")
