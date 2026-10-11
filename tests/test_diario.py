"""Tests de cuando toca el resumen diario."""

from datetime import date, datetime, time

import pytest

from crypto_tracker.config import ConfigError
from crypto_tracker.diario import es_hora_tranquila, leer_hora, toca_resumen

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


# --- horas tranquilas ---


@pytest.mark.parametrize(
    "ahora,tranquila",
    [
        (time(22, 59), False),
        (time(23, 0), True),
        (time(3, 0), True),  # cruza la medianoche
        (time(7, 59), True),
        (time(8, 0), False),
        (time(15, 0), False),
    ],
)
def test_tramo_de_noche(ahora, tranquila):
    assert es_hora_tranquila(ahora, time(23, 0), time(8, 0)) is tranquila


@pytest.mark.parametrize(
    "ahora,tranquila",
    [
        (time(13, 59), False),
        (time(14, 0), True),
        (time(15, 59), True),
        (time(16), False),
    ],
)
def test_tramo_de_dia(ahora, tranquila):
    # la siesta: sin cruzar la medianoche
    assert es_hora_tranquila(ahora, time(14, 0), time(16, 0)) is tranquila


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("8:30", time(8, 30)),
        ("9", time(9, 0)),
        ("a las 21:00", time(21, 0)),
        ("0:00", time(0, 0)),
        ("no", None),
        ("Nunca", None),
    ],
)
def test_leer_hora(texto, esperado):
    assert leer_hora(texto) == esperado


@pytest.mark.parametrize("texto", ["mañana", "25:00", "8:75"])
def test_leer_hora_mal(texto):
    with pytest.raises(ConfigError, match="/horario 8:30"):
        leer_hora(texto)
