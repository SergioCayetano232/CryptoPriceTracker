"""Tests de /futuro."""

import math
from datetime import date, timedelta

import pytest

from crypto_tracker.alerts import formatear_futuro
from crypto_tracker.futuro import (
    DIAS,
    MIN_CAMBIOS,
    Futuro,
    FuturoError,
    calcular,
    interpretar,
)

INICIO = date(2026, 9, 1)


def _dias(valores, desde=INICIO):
    return [(desde + timedelta(days=i), v) for i, v in enumerate(valores)]


def _vaiven(n, sube=1.02):
    """Sube y baja lo mismo cada día: se mueve pero no va a ningún lado."""
    return [1000 * (sube if i % 2 else 1) for i in range(n)]


@pytest.mark.parametrize(
    "texto, esperado",
    [("", DIAS), ("90d", 90), ("7", 7), ("90 días", 90), ("1 dia", 1)],
)
def test_interpretar(texto, esperado):
    assert interpretar(texto) == esperado


@pytest.mark.parametrize("texto", ["0", "400d", "mañana", "3m"])
def test_interpretar_mal(texto):
    with pytest.raises(FuturoError):
        interpretar(texto)


def test_rango_simetrico_en_logaritmos():
    f = calcular(1000, _dias(_vaiven(31)), 30)

    bajo, alto = f.probable
    assert bajo * alto == pytest.approx(1000**2)
    assert bajo < 1000 < alto
    assert f.casi_seguro[0] < bajo and f.casi_seguro[1] > alto
    assert f.contados == 30


def test_crece_con_la_raiz_de_los_dias():
    f7 = calcular(1000, _dias(_vaiven(31)), 7)
    f28 = calcular(1000, _dias(_vaiven(31)), 28)

    ancho7 = math.log(f7.probable[1] / 1000)
    ancho28 = math.log(f28.probable[1] / 1000)
    assert ancho28 == pytest.approx(2 * ancho7)


def test_al_dia():
    f = calcular(1000, _dias(_vaiven(31)), 30)
    # Un 2% arriba y abajo cada día: se mueve en torno a un 2% al día.
    assert 1.9 < f.al_dia < 2.1


def test_quieta_no_se_mueve():
    f = calcular(1000, _dias([1000] * 20), 30)
    assert f.probable == (1000, 1000)


def test_el_salto_de_un_hueco_no_cuenta():
    # Con el bot parado un mes y el precio doblado al volver: ese salto no es un día.
    seguidos = _dias(_vaiven(10))
    despues = _dias([v * 2 for v in _vaiven(10)], desde=INICIO + timedelta(days=30))
    f = calcular(1000, seguidos + despues, 30)

    assert f.contados == 18
    assert 1.9 < f.al_dia < 2.1


def test_pocos_dias():
    assert calcular(1000, _dias(_vaiven(MIN_CAMBIOS)), 30) is None


def test_formatear():
    f = Futuro(10000.0, 30, 2.7, 58, (8600.0, 11600.0), (7800.0, 12800.0))
    texto = formatear_futuro(f, "eur")

    assert "🔮 <b>Tu cartera dentro de 30 días</b>" in texto
    assert "Hoy vale <b>€10.000,00</b>" in texto
    assert "2 de cada 3 veces: entre €8.600,00 y €11.600,00" in texto
    assert "9 de cada 10: entre €7.800,00 y €12.800,00" in texto
    assert "un 2,7% al día" in texto
    assert "58 días" in texto
    assert "No es una predicción" in texto


def test_formatear_un_dia():
    f = Futuro(10000.0, 1, 2.7, 58, (9700.0, 10300.0), (9500.0, 10500.0))
    assert "<b>Tu cartera mañana</b>" in formatear_futuro(f, "eur")
