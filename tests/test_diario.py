"""Tests de cuando toca el resumen diario."""

from datetime import date, datetime, time

import pytest

from crypto_tracker.diario import toca_resumen

NUEVE = time(9, 0)
HOY = date(2026, 9, 29)


def _a_las(h, m=0):
    return datetime(2026, 9, 29, h, m)


@pytest.mark.parametrize(
    "ahora,toca",
    [
        (_a_las(8, 59), False),  # aun no
        (_a_las(9, 0), True),
        (_a_las(9, 4), True),  # el ciclo de las 9 cayo un poco tarde
        (_a_las(10, 30), True),  # estaba apagado, lo manda al volver
        (_a_las(11, 0), True),
        (_a_las(11, 1), False),  # demasiado tarde, hoy se salta
        (_a_las(23, 0), False),  # recien instalado de noche: nada
    ],
)
def test_la_hora(ahora, toca):
    assert toca_resumen(ahora, NUEVE, None) is toca


def test_no_se_repite_el_mismo_dia():
    assert toca_resumen(_a_las(9, 5), NUEVE, HOY) is False


def test_al_dia_siguiente_vuelve():
    ayer = date(2026, 9, 28)

    assert toca_resumen(_a_las(9, 0), NUEVE, ayer) is True
