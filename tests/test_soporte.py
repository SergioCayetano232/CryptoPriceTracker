"""Tests de /soporte."""

from datetime import date, datetime, timedelta, timezone

import pytest

from crypto_tracker.alerts import formatear_soporte
from crypto_tracker.periodo import PeriodoError
from crypto_tracker.soporte import (
    POR_DEFECTO,
    Nivel,
    Soportes,
    agrupar,
    calcular,
    giros,
    interpretar,
    velas,
)

INICIO = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)


def _serie(precios):
    """Un precio al día, a mediodía."""
    return [(INICIO + timedelta(days=i), p) for i, p in enumerate(precios)]


def _dia(n):
    return (INICIO + timedelta(days=n)).astimezone().date()


# Rebota dos veces en 90 y choca dos veces con 110; hoy está a 100.
ZIGZAG = [100, 95, 90, 95, 100, 105, 110, 105, 100, 95, 91, 95, 100, 105, 109, 104, 100]


def test_interpretar():
    assert interpretar("btc 30d") == ("bitcoin", 720)
    assert interpretar("") == ("", POR_DEFECTO)
    with pytest.raises(PeriodoError):
        interpretar("btc eth")


def test_velas_por_dia():
    serie = [
        (INICIO, 100.0),
        (INICIO + timedelta(hours=2), 108.0),
        (INICIO + timedelta(hours=4), 97.0),
        (INICIO + timedelta(days=1), 101.0),
    ]
    assert velas(serie) == [(_dia(0), 108.0, 97.0), (_dia(1), 101.0, 101.0)]


def test_giros():
    dias = velas(_serie(ZIGZAG))
    assert [p for _, p in giros(dias)] == [90, 110, 91, 109]


def test_precio_plano_no_da_giros():
    assert giros(velas(_serie([100] * 10))) == []


def test_agrupar_los_cercanos():
    puntos = [(_dia(2), 90.0), (_dia(10), 91.0), (_dia(6), 110.0)]
    [nivel] = agrupar(puntos)

    assert nivel.precio == pytest.approx(90.5)
    assert nivel.toques == 2
    assert nivel.ultimo == _dia(10)


def test_calcular():
    s = calcular(_serie(ZIGZAG))

    assert s.precio == 100
    assert [round(n.precio, 1) for n in s.soportes] == [90.5]
    assert [round(n.precio, 1) for n in s.resistencias] == [109.5]
    assert s.distancia(s.soportes[0]) == pytest.approx(-9.5)


def test_el_mas_cercano_primero():
    def bache(fondo):
        return [100, 100, fondo, 100]

    zigzag = [100] + bache(80) + bache(90) + bache(81) + bache(91) + [100, 100]
    s = calcular(_serie(zigzag))

    assert [round(n.precio) for n in s.soportes] == [90, 80]


def test_pocos_dias():
    assert calcular(_serie([100, 90, 100])) is None


def test_formatear():
    s = Soportes(
        100.0,
        [Nivel(90.5, 2, date(2026, 9, 11))],
        [Nivel(109.5, 3, date(2026, 9, 15))],
    )
    texto = formatear_soporte("bitcoin", s, POR_DEFECTO, "eur")

    assert "🧱 <b>Bitcoin</b>: soportes y resistencias" in texto
    assert "Está a <b>€100,00</b>" in texto
    assert "🔴 €109,50 · 3 toques, el último el 15/09 · <b>+9,5%</b>" in texto
    assert "🟢 €90,50 · 2 toques, el último el 11/09 · <b>-9,5%</b>" in texto
    assert "/alerta bitcoin 90.5" in texto


def test_formatear_sin_nada_por_arriba():
    s = Soportes(120.0, [Nivel(90.5, 2, date(2026, 9, 11))], [])
    texto = formatear_soporte("bitcoin", s, POR_DEFECTO, "eur")

    assert "Ninguna por arriba" in texto


def test_formatear_sin_ninguno():
    texto = formatear_soporte("bitcoin", Soportes(100.0, [], []), POR_DEFECTO, "eur")

    assert "No ha girado dos veces en el mismo sitio" in texto
