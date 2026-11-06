"""Tests de /rentabilidad."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.alerts import formatear_rentabilidad
from crypto_tracker.movimientos import Movimiento
from crypto_tracker.rentabilidad import Rentabilidad, calcular, contables, tir

INICIO = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _dia(n):
    return INICIO + timedelta(days=n)


def _mov(id, coin, tipo, cantidad, coste, dia):
    return Movimiento(id, coin, tipo, cantidad, coste, None, _dia(dia))


def test_tir_un_año_al_10():
    assert tir([(_dia(0), -1000), (_dia(365), 1100)]) == pytest.approx(0.10)


def test_tir_dos_años():
    # 1.000 que pasan a 1.210 en dos años: un 10% cada año, no un 21%
    assert tir([(_dia(0), -1000), (_dia(730), 1210)]) == pytest.approx(0.10)


def test_tir_cuenta_cuando_entra_el_dinero():
    # Lo segundo solo ha estado medio año: al año sale más de lo que parece.
    flujos = [(_dia(0), -1000), (_dia(182), -1000), (_dia(365), 2150)]
    assert tir(flujos) == pytest.approx(0.1007, abs=0.0005)


def test_tir_pierdes():
    assert tir([(_dia(0), -1000), (_dia(365), 500)]) == pytest.approx(-0.5)


def test_tir_sin_solucion():
    assert tir([(_dia(0), -1000), (_dia(365), -500)]) is None


def test_calcular():
    lista = [
        _mov(1, "bitcoin", "compra", 0.02, 1000, 0),
        _mov(2, "bitcoin", "venta", 0.01, 600, 200),
    ]
    r = calcular(lista, {"bitcoin": 55000.0}, _dia(365))

    assert r.metido == 1000
    assert r.sacado == 600
    assert r.vale == pytest.approx(550)
    assert r.ganancia == pytest.approx(150)
    assert r.porcentaje == pytest.approx(15)
    assert r.dias == 365
    # Más que el 15% total: parte del dinero volvió a los 200 días.
    assert r.anual == pytest.approx(20.2, abs=0.1)
    assert r.fuera == 0


def test_menos_de_un_mes_no_va_a_anual():
    r = calcular(
        [_mov(1, "bitcoin", "compra", 0.02, 1000, 0)], {"bitcoin": 55000.0}, _dia(10)
    )

    assert r.porcentaje == pytest.approx(10)
    assert r.anual is None


def test_fuera_lo_sin_precio_y_las_ventas_del_env():
    lista = [
        _mov(1, "bitcoin", "compra", 0.02, 1000, 0),
        _mov(2, "bitcoin", "compra", 0.01, None, 10),
        _mov(3, "ethereum", "venta", 1, 3000, 20),
    ]
    dentro, tienes = contables(lista)

    assert [m.id for m in dentro] == [1]
    assert tienes == {"bitcoin": 0.02}
    assert calcular(lista, {"bitcoin": 50000.0}, _dia(100)).fuera == 2


def test_vendido_todo():
    lista = [
        _mov(1, "bitcoin", "compra", 0.02, 1000, 0),
        _mov(2, "bitcoin", "venta", 0.02, 1500, 365),
    ]
    r = calcular(lista, {}, _dia(365))

    assert r.vale == 0
    assert r.anual == pytest.approx(50)


def test_nada_o_sin_precio_de_hoy():
    assert calcular([], {}, _dia(0)) is None
    lista = [_mov(1, "bitcoin", "compra", 0.02, 1000, 0)]
    assert calcular(lista, {}, _dia(100)) is None


def _r(**cambios):
    datos = dict(metido=1000, sacado=600, vale=550, dias=365, anual=17.5, fuera=0)
    return Rentabilidad(**{**datos, **cambios})


def test_formatear():
    texto = formatear_rentabilidad(_r(), "eur")

    assert "📈 <b>Tu rentabilidad</b>" in texto
    assert "Has metido €1.000,00 y sacado €600,00" in texto
    assert "Lo que te queda vale €550,00" in texto
    assert "🔺 Ganas <b>+€150,00</b> (+15,0%) en 365 días" in texto
    assert "📅 Al año, un <b>+17,5%</b>" in texto
    assert "cuándo metiste" in texto


def test_formatear_sin_ventas():
    texto = formatear_rentabilidad(_r(sacado=0, vale=1200), "eur")

    assert "Has metido €1.000,00. Hoy vale €1.200,00" in texto


def test_formatear_pierdes():
    texto = formatear_rentabilidad(_r(sacado=0, vale=800, anual=-20.0), "eur")

    assert "🔻 Pierdes <b>-€200,00</b> (-20,0%)" in texto
    assert "<b>-20,0%</b>" in texto


def test_formatear_poco_tiempo():
    texto = formatear_rentabilidad(_r(dias=12, anual=None), "eur")

    assert "en 12 días" in texto
    assert "Con menos de un mes no lo paso a anual" in texto


def test_formatear_un_dia_y_fuera():
    texto = formatear_rentabilidad(_r(dias=1, anual=None, fuera=2), "eur")

    assert "en 1 día" in texto
    assert "2 movimientos no cuentan" in texto
