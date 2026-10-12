"""Tests de /rango."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.alerts import formatear_rango
from crypto_tracker.periodo import PeriodoError
from crypto_tracker.rango import Rango, barra, calcular, interpretar

INICIO = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)


def _serie(*precios):
    return [(INICIO + timedelta(days=i), p) for i, p in enumerate(precios)]


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("bitcoin 30d", ("bitcoin", 720)),
        ("btc", ("bitcoin", 168)),  # sin tramo, 7 dias
        ("12h", ("", 12)),  # sin cripto, la primera que vigila
        ("", ("", 168)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


def test_interpretar_formato_malo():
    with pytest.raises(PeriodoError, match="/rango bitcoin 7d"):
        interpretar("bitcoin ethereum 7d")


def test_calcular():
    r = calcular(_serie(100, 120, 80, 110))

    assert (r.maximo, r.minimo, r.ahora) == (120, 80, 110)
    assert r.cuando_maximo == INICIO + timedelta(days=1)
    assert r.cuando_minimo == INICIO + timedelta(days=2)
    assert r.media == 102.5
    assert r.posicion == 75


def test_calcular_con_empate_se_queda_el_ultimo():
    r = calcular(_serie(120, 100, 120, 110))

    assert r.cuando_maximo == INICIO + timedelta(days=2)


def test_calcular_sin_datos():
    assert calcular([]) is None
    assert calcular(_serie(100)) is None


def test_calcular_sin_moverse():
    assert calcular(_serie(100, 100)).posicion is None


@pytest.mark.parametrize(
    "posicion,esperado",
    [(0, "●━━━━━━━━━"), (100, "━━━━━━━━━●"), (50, "━━━━●━━━━━")],
)
def test_barra(posicion, esperado):
    assert barra(posicion) == esperado


def test_formatear():
    r = Rango(120, INICIO, 80, INICIO + timedelta(days=2), 102.5, 110)

    texto = formatear_rango("bitcoin", r, 168, "eur")

    assert "📏 <b>Bitcoin</b>, últimos 7 días" in texto
    assert "Máximo €120,00" in texto
    assert "ahora -8.33%" in texto
    assert "Mínimo €80,00" in texto
    assert "ahora +37.50%" in texto
    assert "Media €102,50" in texto
    assert "Ahora <b>€110,00</b>, al 75% del rango" in texto
    assert "<code>mín ━━━━━━━●━━ máx</code>" in texto
    assert "Solo tengo" not in texto


def test_formatear_sin_moverse_y_con_hueco():
    r = Rango(100, INICIO, 100, INICIO, 100, 100)

    texto = formatear_rango("bitcoin", r, 168, "eur", desde=INICIO)

    assert "No se ha movido nada" in texto
    assert "mín" not in texto
    assert "Solo tengo precios desde el" in texto
