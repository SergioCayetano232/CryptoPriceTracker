"""Tests de las velas de /historico."""

from datetime import datetime, timedelta

import pytest

from crypto_tracker.velas import Vela, agrupar, pedidas, tamaño

AQUI = datetime(2026, 11, 20, 0, 0).astimezone()


def _a(horas, minutos=0):
    return AQUI + timedelta(hours=horas, minutes=minutos)


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("btc 7d", (False, "btc 7d")),
        ("btc 7d velas", (True, "btc 7d")),
        ("VELAS btc", (True, "btc")),
        ("velas", (True, "")),
    ],
)
def test_pedidas(texto, sale):
    assert pedidas(texto) == sale


@pytest.mark.parametrize(
    "horas, sale", [(24, 1), (48, 1), (72, 4), (7 * 24, 4), (30 * 24, 24)]
)
def test_tamaño(horas, sale):
    assert tamaño(horas) == sale


def test_agrupar_por_horas():
    serie = [
        (_a(0, 5), 100.0),
        (_a(0, 30), 110.0),
        (_a(0, 55), 95.0),
        (_a(1, 10), 96.0),
        (_a(1, 40), 90.0),
    ]

    a, b = agrupar(serie, 1)

    assert a == Vela(_a(0), 100, 110, 95, 95)
    assert b == Vela(_a(1), 96, 96, 90, 90)
    assert not a.sube


def test_agrupar_de_4_en_4_empieza_en_hora_redonda():
    serie = [(_a(5, 10), 100.0), (_a(7, 50), 120.0), (_a(8, 5), 121.0)]

    a, b = agrupar(serie, 4)

    assert (a.inicio, a.apertura, a.cierre) == (_a(4), 100, 120)
    assert a.sube
    assert b.inicio == _a(8)


def test_agrupar_por_dias_en_la_hora_de_aqui():
    # Ordenadas por hora aunque lleguen desordenadas por día.
    serie = [(_a(23, 50), 10.0), (_a(24, 10), 12.0), (_a(47), 11.0)]

    a, b = agrupar(serie, 24)

    assert a.inicio == AQUI
    assert (b.inicio, b.apertura, b.cierre, b.alto) == (_a(24), 12, 11, 12)


def test_agrupar_nada():
    assert agrupar([], 1) == []
