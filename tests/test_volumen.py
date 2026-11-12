"""Tests del aviso de volumen raro."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.alerts import formatear_volumen
from crypto_tracker.volumen import Volumen, normal, sigue, toca

AHORA = datetime(2026, 11, 12, 12, tzinfo=timezone.utc)


def _hace(dias, horas=0):
    return AHORA - timedelta(days=dias, hours=horas)


def _vol(veces, cambio=6.2):
    return Volumen("bitcoin", veces * 10e9, 10e9, 80000.0, cambio)


def test_normal_es_la_mediana():
    serie = [(_hace(10), 8e9), (_hace(5), 10e9), (_hace(2), 30e9)]
    assert normal(serie, AHORA) == 10e9


def test_normal_sin_lo_de_las_ultimas_24h():
    # Lo de hace 3 horas ya lleva el subidón de hoy: no cuenta como normal.
    serie = [(_hace(8), 10e9), (_hace(0, 3), 90e9), (_hace(0, 1), 95e9)]
    assert normal(serie, AHORA) == 10e9


def test_normal_con_poca_historia():
    assert normal([(_hace(3), 10e9)], AHORA) is None
    assert normal([], AHORA) is None


def test_normal_sin_volumen():
    assert normal([(_hace(8), 0.0)], AHORA) is None


@pytest.mark.parametrize(
    "veces, avisado, esperado",
    [(3.4, False, True), (2.9, False, False), (5.0, True, False)],
)
def test_toca(veces, avisado, esperado):
    assert toca(_vol(veces), avisado) is esperado


@pytest.mark.parametrize(
    "veces, avisado, esperado",
    [
        (3.4, False, True),
        (2.5, True, True),  # sigue movido: no repite
        (1.8, True, False),  # se ha calmado: la próxima vez avisa
        (2.5, False, False),
    ],
)
def test_sigue(veces, avisado, esperado):
    assert sigue(_vol(veces), avisado) is esperado


def test_formatear():
    texto = formatear_volumen(_vol(3.4), "eur")

    assert "📢 <b>Bitcoin mueve mucho más de lo normal</b>" in texto
    assert "€34.000 millones negociados en 24 h, 3,4 veces lo normal" in texto
    assert "Está a €80.000,00 (🔺 +6,2% en 24 h)" in texto
    assert "No repito hasta que se calme" in texto


def test_formatear_sin_cambio():
    texto = formatear_volumen(_vol(4, cambio=None), "eur")

    assert "Está a €80.000,00\n" in texto
