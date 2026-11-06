"""Tests del resumen mensual."""

from datetime import date, datetime, time

from crypto_tracker.mensual import toca, tramo


def _aqui(*args):
    return datetime(*args).astimezone()


def test_toca_el_dia_1_a_su_hora():
    assert toca(_aqui(2026, 11, 1, 9, 5), time(9, 0), None)


def test_no_toca_otro_dia():
    assert not toca(_aqui(2026, 11, 2, 9, 5), time(9, 0), None)


def test_no_toca_antes_de_la_hora():
    assert not toca(_aqui(2026, 11, 1, 8, 59), time(9, 0), None)


def test_no_repite_el_mismo_dia():
    assert not toca(_aqui(2026, 11, 1, 9, 30), time(9, 0), date(2026, 11, 1))


def test_tramo():
    desde, hasta = tramo(_aqui(2026, 11, 1, 9, 5))

    assert desde == _aqui(2026, 10, 1)
    assert hasta == _aqui(2026, 11, 1)


def test_tramo_en_enero_es_diciembre_del_año_pasado():
    desde, hasta = tramo(_aqui(2027, 1, 1, 9, 5))

    assert desde == _aqui(2026, 12, 1)
    assert hasta == _aqui(2027, 1, 1)


def test_tramo_en_marzo_coge_febrero_entero():
    desde, _ = tramo(_aqui(2028, 3, 1, 9, 5))

    assert desde == _aqui(2028, 2, 1)
