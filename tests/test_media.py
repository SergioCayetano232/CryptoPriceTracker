"""Tests de /media."""

from datetime import date, timedelta

import pytest

from crypto_tracker.alerts import formatear_media
from crypto_tracker.media import calcular, interpretar, lado_de_todas
from crypto_tracker.periodo import PeriodoError

HOY = date(2026, 10, 12)


def _dias(*precios):
    """Un precio por día, el último es hoy."""
    n = len(precios)
    return [(HOY - timedelta(days=n - 1 - i), p) for i, p in enumerate(precios)]


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("bitcoin", ("bitcoin", (7, 30, 90))),
        ("btc 30d", ("bitcoin", (30,))),
        ("14d", ("", (14,))),
        ("", ("", (7, 30, 90))),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


@pytest.mark.parametrize("argumento", ["btc 12h", "btc 1d", "btc 36h"])
def test_interpretar_tramo_que_no_son_dias(argumento):
    with pytest.raises(PeriodoError, match="en días"):
        interpretar(argumento)


def test_interpretar_de_varias():
    with pytest.raises(PeriodoError, match="/media bitcoin 30d"):
        interpretar("btc eth")


def test_calcular_solo_los_ultimos_dias():
    dias = _dias(1000, 100, 110, 120, 130, 140, 150, 160)

    assert calcular(dias, 7) == pytest.approx(130)  # el 1000 se queda fuera


def test_calcular_sin_bastantes_dias():
    assert calcular(_dias(100, 110, 120, 130, 140), 7) is None  # 5 de 7
    assert calcular(_dias(100, 110, 120, 130, 140, 150), 7) == pytest.approx(125)
    assert calcular([], 7) is None


def test_formatear():
    texto = formatear_media("bitcoin", 110.0, {7: 100.0, 30: 125.0, 90: None}, "eur")

    assert "📐 <b>Bitcoin</b>  ahora €110,00" in texto
    assert "Media de 7 días  €100,00  🔺 +10.00% por encima" in texto
    assert "Media de 30 días  €125,00  🔻 -12.00% por debajo" in texto
    assert "Media de 90 días  <i>no tengo tantos días guardados</i>" in texto


def test_lado_de_todas():
    assert lado_de_todas(110, {7: 100, 30: 105, 90: 90}) is True
    assert lado_de_todas(80, {7: 100, 30: 105, 90: None}) is False
    assert lado_de_todas(102, {7: 100, 30: 105}) is None
    assert lado_de_todas(110, {7: 100, 30: None, 90: None}) is None
    assert lado_de_todas(100, {7: 100, 30: 90}) is None


def test_formatear_por_encima_o_debajo_de_todas():
    arriba = formatear_media("btc", 130.0, {7: 100.0, 30: 125.0}, "eur")
    abajo = formatear_media("btc", 90.0, {7: 100.0, 30: 125.0}, "eur")
    una = formatear_media("btc", 130.0, {14: 100.0}, "eur")

    assert "🟢 Por encima de todas: va hacia arriba" in arriba
    assert "🔴 Por debajo de todas: va hacia abajo" in abajo
    assert "de todas" not in una
