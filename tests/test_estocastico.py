"""Tests de /estocastico."""

from datetime import date, datetime, timedelta, timezone

import pytest

from crypto_tracker.estocastico import MINIMO, Vela, calcular, velas

INICIO = date(2026, 9, 1)


def _velas(cierres, desde=INICIO):
    # Cada día se mueve 1 arriba y 1 abajo de donde cierra.
    return [
        Vela(desde + timedelta(days=i), c + 1, c - 1, c) for i, c in enumerate(cierres)
    ]


def test_velas_de_lo_guardado():
    dia = datetime(2026, 9, 1, 10, tzinfo=timezone.utc)
    serie = [
        (dia, 100.0),
        (dia + timedelta(hours=2), 120.0),
        (dia + timedelta(hours=4), 90.0),
    ]

    [v] = velas(serie)

    assert (v.alto, v.bajo, v.cierre) == (120, 90, 90)


def test_subiendo_sin_parar_es_sobrecompra():
    e = calcular(_velas([100.0 + i for i in range(30)]))

    # Cierra a 129, el rango es de 115 a 130: (129-115)/15.
    assert e.k == pytest.approx(14 / 15 * 100)
    assert e.zona == "alto"
    assert e.techo == 130
    assert e.suelo == 115
    assert e.ahora == 129


def test_bajando_sin_parar_es_sobreventa():
    e = calcular(_velas([200.0 - i for i in range(30)]))

    assert e.k == pytest.approx(1 / 15 * 100)
    assert e.zona == "bajo"


def test_sin_moverse_queda_en_medio():
    lista = [Vela(INICIO + timedelta(days=i), 100, 100, 100) for i in range(20)]

    e = calcular(lista)

    assert e.k == 50
    assert e.zona == "medio"


def test_d_es_la_media_de_tres():
    e = calcular(_velas([100.0 + i for i in range(30)]))

    # En una recta los tres últimos %K son iguales.
    assert e.d == pytest.approx(e.k)


def test_cruce_al_girar():
    # Baja 25 días y rebota 3 con fuerza: %K pasa por encima de %D.
    cierres = [200.0 - 2 * i for i in range(25)] + [160.0, 170.0, 180.0]

    e = calcular(_velas(cierres))

    assert e.cruce_arriba
    assert e.cruce_hace is not None
    assert e.cruce_hace <= 2


def test_pocos_dias():
    assert calcular(_velas([100.0] * MINIMO)) is None
    assert calcular(_velas([100.0] * (MINIMO + 1))) is not None


def test_solo_el_ultimo_tramo_sin_huecos():
    antes = _velas([100.0] * 20)
    despues = _velas([100.0] * 5, desde=INICIO + timedelta(days=40))

    assert calcular(antes + despues) is None
