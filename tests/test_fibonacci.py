"""Tests de /fibonacci."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.alerts import formatear_fibonacci
from crypto_tracker.fibonacci import (
    POR_DEFECTO,
    calcular,
    interpretar,
)
from crypto_tracker.periodo import PeriodoError

INICIO = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)


def _serie(valores):
    return [(INICIO + timedelta(days=i), v) for i, v in enumerate(valores)]


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("", ("", POR_DEFECTO)),
        ("btc", ("bitcoin", POR_DEFECTO)),
        ("bitcoin 30d", ("bitcoin", 720)),
        ("7d", ("", 168)),
    ],
)
def test_interpretar(texto, esperado):
    assert interpretar(texto) == esperado


def test_interpretar_mal():
    with pytest.raises(PeriodoError):
        interpretar("btc eth 30d")


def test_subiendo():
    # De 100 a 200 y corrige a 150: justo en el 50%.
    f = calcular(_serie([100.0, 140.0, 200.0, 170.0, 150.0]))

    assert f.subiendo
    precios = {n.pct: round(n.precio, 2) for n in f.niveles}
    assert precios == {
        0.0: 200,
        23.6: 176.4,
        38.2: 161.8,
        50.0: 150,
        61.8: 138.2,
        78.6: 121.4,
        100.0: 100,
    }
    assert [n.precio for n in f.niveles] == sorted(
        (n.precio for n in f.niveles), reverse=True
    )
    assert f.debajo.pct == 61.8
    assert f.encima.pct == 38.2


def test_bajando():
    # De 200 a 100 y rebota a 130.
    f = calcular(_serie([200.0, 150.0, 100.0, 130.0]))

    assert not f.subiendo
    precios = {n.pct: round(n.precio, 2) for n in f.niveles}
    assert precios[0.0] == 100 and precios[100.0] == 200
    assert precios[61.8] == 161.8
    assert f.niveles[0].pct == 100.0  # el más alto arriba
    assert f.debajo.pct == 23.6
    assert f.encima.pct == 38.2


def test_en_el_maximo():
    f = calcular(_serie([100.0, 150.0, 200.0]))
    assert f.encima is None
    assert f.debajo.pct == 23.6


@pytest.mark.parametrize("valores", [[], [100.0], [100.0, 100.5, 100.2], [0.0, 5.0]])
def test_sin_niveles(valores):
    assert calcular(_serie(valores)) is None


def test_formatear():
    f = calcular(_serie([100.0, 140.0, 200.0, 170.0, 150.5]))
    texto = formatear_fibonacci("bitcoin", f, 90 * 24, "eur")
    lineas = texto.split("\n")

    assert "🌀 <b>Bitcoin</b>: Fibonacci, últimos 90 días" in texto
    assert "Subió de €100,00 (01/09) a €200,00 (03/09)" in texto
    assert "0%: €200,00 · el máximo" in texto
    assert "61,8%: €138,20" in texto
    assert "100%: €100,00 · el mínimo" in texto
    # El precio de ahora va entre el 38,2% y el 50%.
    ahora = lineas.index("👉 <b>Ahora €150,50</b>")
    assert lineas[ahora - 1].startswith("38,2%")
    assert lineas[ahora + 1].startswith("50%")
    assert "🛟 Por debajo, el 50% (€150,00), a un -0,3%" in texto
    assert "🧱 Por encima, el 38,2% (€161,80), a un +7,5%" in texto
    assert "Solo tengo precios" not in texto


def test_formatear_bajando_y_corto():
    f = calcular(_serie([200.0, 150.0, 100.0, 130.0]))
    texto = formatear_fibonacci("bitcoin", f, 90 * 24, "eur", desde=INICIO)

    assert (
        "Bajó de €200,00 (01/09) a €100,00 (03/09): hasta dónde podría rebotar" in texto
    )
    assert "100%: €200,00 · el máximo" in texto
    assert "0%: €100,00 · el mínimo" in texto
    assert "Solo tengo precios desde el 01/09" in texto


def test_formatear_en_el_minimo():
    f = calcular(_serie([200.0, 150.0, 100.0]))
    texto = formatear_fibonacci("bitcoin", f, 90 * 24, "eur")

    assert texto.split("\n").index("👉 <b>Ahora €100,00</b>") > 0
    assert "Por debajo" not in texto


def test_formatear_con_miles_y_el_minimo_por_debajo():
    f = calcular(_serie([87158.43, 70000.0, 62612.09, 64870.22]))
    texto = formatear_fibonacci("bitcoin", f, 90 * 24, "usd")

    assert "🛟 Por debajo, el mínimo ($62.612,09), a un -3,5%" in texto
    assert "🧱 Por encima, el 23,6% ($68.405,03), a un +5,4%" in texto
