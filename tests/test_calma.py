"""Tests del aviso de calma y de /calma."""

from datetime import date, timedelta

import pytest

from crypto_tracker.calma import Calma, calcular, sigue, toca

INICIO = date(2026, 8, 1)


def _dias(precios):
    return [(INICIO + timedelta(days=i), p) for i, p in enumerate(precios)]


def _movida(n, desde=100.0):
    """Sube y baja un 5% día sí día no."""
    return [desde * (1.05 if i % 2 else 1.0) for i in range(n)]


def test_semana_quieta_tras_semanas_movidas():
    precios = _movida(50) + [100.0, 100.5, 100.2, 100.4, 100.1, 100.3, 100.2]

    c = calcular(_dias(precios))

    assert c.quieta
    assert c.puesto == 0
    assert c.suelo == 100 and c.techo == 100.5
    assert c.rango == pytest.approx(0.5, abs=0.01)
    # Un 5% sobre la media de la semana, que según el día lleva 3 o 4 altos.
    assert c.normal == pytest.approx(4.9, abs=0.05)


def test_semana_normal_no_es_calma():
    c = calcular(_dias(_movida(60)))

    assert not c.quieta


def test_poca_historia():
    # 36 días dan 30 semanas que mirar: hace falta una más.
    assert calcular(_dias(_movida(36))) is None
    assert calcular(_dias(_movida(37))) is not None


def test_lo_que_paso_despues_de_las_otras_veces():
    # Dos semanas quietas, y a los 7 días de cada una, un 10% más arriba.
    precios = (
        _movida(20)
        + [100.0] * 7
        + _movida(20, 110)
        + [110.0] * 7
        + _movida(20, 121)
        + [121.0, 121.1, 121.0, 121.1, 121.0, 121.1, 121.0]
    )

    c = calcular(_dias(precios))

    assert c.quieta
    assert c.veces == 2
    assert c.despues == pytest.approx(10)


def test_avisa_una_vez_y_se_rearma_al_moverse():
    quieta = Calma(1, 1, 1, 5, 0.05, 0, None, 60)
    a_medias = Calma(1, 1, 1, 5, 0.20, 0, None, 60)
    movida = Calma(1, 1, 1, 5, 0.50, 0, None, 60)

    assert toca(quieta, False)
    assert not toca(quieta, True)
    assert sigue(a_medias, True)  # aún no se ha movido lo bastante
    assert not sigue(movida, True)
    assert not sigue(movida, False)
