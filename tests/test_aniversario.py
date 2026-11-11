"""Tests de las compras que cumplen años en el resumen."""

from datetime import date, datetime

import pytest

from crypto_tracker.alerts import formatear_aniversarios
from crypto_tracker.aniversario import Aniversario, calcular, de_hoy
from crypto_tracker.movimientos import Movimiento


def _mov(id, dia, tipo="compra", coin_id="bitcoin", cantidad=0.01, coste=600.0):
    cuando = datetime(dia.year, dia.month, dia.day, 12).astimezone()
    return Movimiento(id, coin_id, tipo, cantidad, coste, None, cuando)


def test_las_que_cumplen_hoy():
    movs = [
        _mov(1, date(2024, 11, 11)),
        _mov(2, date(2025, 11, 11)),
        _mov(3, date(2025, 11, 12)),  # mañana
        _mov(4, date(2026, 11, 11)),  # de hoy mismo, aún no cumple
        _mov(5, date(2025, 11, 11), tipo="venta"),
        _mov(6, date(2025, 11, 11), tipo="recompensa"),
    ]

    hoy = de_hoy(movs, date(2026, 11, 11))

    assert [m.id for m in hoy] == [1, 2]
    assert [a.años for a in calcular(hoy, {}, date(2026, 11, 11))] == [2, 1]


def test_29_de_febrero():
    movs = [_mov(1, date(2024, 2, 29))]

    assert de_hoy(movs, date(2025, 2, 28))
    assert not de_hoy(movs, date(2025, 3, 1))
    assert not de_hoy(movs, date(2028, 2, 28))  # bisiesto: toca el 29
    assert de_hoy(movs, date(2028, 2, 29))


def test_lo_que_vale_hoy():
    [a] = calcular([_mov(1, date(2025, 11, 11))], {"bitcoin": 110000.0}, date.today())

    assert a.valor == pytest.approx(1100)
    assert a.cambio == pytest.approx(83.333, abs=0.001)


def test_sin_precio_ni_coste():
    [a] = calcular([_mov(1, date(2025, 11, 11), coste=None)], {}, date.today())

    assert a.valor is None
    assert a.cambio is None


def test_formatear_una():
    a = Aniversario(_mov(1, date(2025, 11, 11)), 1, 110000.0)

    texto = formatear_aniversarios([a], "eur")

    assert texto == (
        "🎂 <b>Hoy cumple años una de tus compras</b>\n"
        "Hace 1 año compraste 0,01 de Bitcoin por €600,00: "
        "hoy vale <b>€1.100,00</b> 🔺 +83.33%"
    )


def test_formatear_sin_precio_ni_coste():
    a = Aniversario(_mov(1, date(2024, 11, 11), coste=None), 2)

    texto = formatear_aniversarios([a], "eur")

    assert texto.endswith("Hace 2 años compraste 0,01 de Bitcoin")


def test_formatear_muchas_se_cortan():
    lista = [Aniversario(_mov(i, date(2025, 11, 11)), 1, 50000.0) for i in range(5)]

    texto = formatear_aniversarios(lista, "eur")

    assert texto.startswith("🎂 <b>Hoy cumplen años 5 de tus compras</b>")
    assert texto.count("Hace 1 año") == 3
    assert texto.endswith("<i>y 2 más</i>")
    assert "🔻 -16.67%" in texto
