"""Tests de /deposito."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.alerts import formatear_deposito
from crypto_tracker.deposito import (
    TIPO,
    Contra,
    DepositoError,
    calcular,
    interpretar,
)
from crypto_tracker.movimientos import Movimiento

INICIO = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _dia(n):
    return INICIO + timedelta(days=n)


def _mov(id, coin, tipo, cantidad, coste, dia):
    return Movimiento(id, coin, tipo, cantidad, coste, None, _dia(dia))


@pytest.mark.parametrize(
    "texto, esperado",
    [("", TIPO), ("3%", 3), ("2,5", 2.5), ("al 4 %", 4), ("1.5%", 1.5)],
)
def test_interpretar(texto, esperado):
    assert interpretar(texto) == esperado


@pytest.mark.parametrize("texto", ["0%", "-2%", "80%", "mucho"])
def test_interpretar_mal(texto):
    with pytest.raises(DepositoError):
        interpretar(texto)


def test_un_año_al_3():
    # 1.000 € en BTC hace un año que hoy valen 1.100
    r = calcular(
        [_mov(1, "bitcoin", "compra", 0.02, 1000, 0)],
        {"bitcoin": 55000.0},
        _dia(365),
        3,
    )

    assert r.real == pytest.approx(1100)
    assert r.deposito == pytest.approx(1030)
    assert r.intereses == pytest.approx(30)
    assert r.diferencia == pytest.approx(70)
    assert r.empate == pytest.approx(10)
    assert r.desde == _dia(0)


def test_cuenta_cuando_entra_cada_euro():
    # Lo segundo solo lleva medio año: pone la mitad de intereses, más o menos.
    lista = [
        _mov(1, "bitcoin", "compra", 0.01, 500, 0),
        _mov(2, "bitcoin", "compra", 0.01, 500, 365 - 182),
    ]
    r = calcular(lista, {"bitcoin": 50000.0}, _dia(365), 4)

    assert r.intereses == pytest.approx(20 + 500 * (1.04 ** (182 / 365) - 1))


def test_una_venta_sale_del_deposito():
    lista = [
        _mov(1, "bitcoin", "compra", 0.02, 1000, 0),
        _mov(2, "bitcoin", "venta", 0.01, 600, 365),
    ]
    r = calcular(lista, {"bitcoin": 55000.0}, _dia(365), 3)

    assert r.real == pytest.approx(550)
    assert r.deposito == pytest.approx(430)


def test_vendiste_mas_de_lo_que_tendria():
    lista = [
        _mov(1, "bitcoin", "compra", 0.02, 1000, 0),
        _mov(2, "bitcoin", "venta", 0.01, 2000, 365),
    ]
    r = calcular(lista, {"bitcoin": 200000.0}, _dia(365), 3)

    assert r.deposito == 0
    assert r.ventaja is None


def test_las_recompensas_solo_cuentan_en_la_cartera():
    lista = [
        _mov(1, "ethereum", "compra", 1.0, 2000, 0),
        _mov(2, "ethereum", "recompensa", 0.1, 200, 100),
    ]
    r = calcular(lista, {"ethereum": 2000.0}, _dia(365), 3)

    assert r.real == pytest.approx(2200)
    assert r.deposito == pytest.approx(2060)


def test_sin_precio_de_hoy():
    lista = [_mov(1, "bitcoin", "compra", 0.02, 1000, 0)]
    assert calcular(lista, {}, _dia(365), 3) is None


def test_sin_lo_que_costaron():
    lista = [_mov(1, "bitcoin", "compra", 0.02, None, 0)]
    assert calcular(lista, {"bitcoin": 50000.0}, _dia(365), 3) is None


def _contra(real, deposito, empate=10.0, fuera=0):
    return Contra(real, deposito, deposito - 1000, 3.0, _dia(0), empate, fuera)


def test_formatear_ganas_tu():
    texto = formatear_deposito(_contra(1100, 1030), "eur")

    assert "🏦 <b>Tu cartera contra un depósito al 3%</b>" in texto
    assert "Lo que compraste vale hoy <b>€1.100,00</b>" in texto
    assert "sería €1.030,00 (€30,00 de intereses)" in texto
    assert "🏆 Le ganas al depósito por <b>€70,00</b> (+6,8%)" in texto
    assert "el depósito tendría que dar un <b>10,0%</b> al año" in texto
    assert "desde el 01/01/2025" in texto


def test_formatear_gana_el_deposito():
    texto = formatear_deposito(_contra(900, 1030, empate=-10.0), "eur")

    assert "🐢 El depósito te gana por <b>€130,00</b> (-12,6%)" in texto
    assert "Tu cartera pierde un 10,0% al año: cualquier depósito le gana" in texto


def test_formatear_sin_tir_ni_deposito():
    texto = formatear_deposito(_contra(500, 0, empate=None, fuera=2), "eur")

    assert "🏆 Le ganas al depósito por <b>€500,00</b>\n" in texto
    assert "de intereses" not in texto
    assert "📅" not in texto
    assert "2 movimientos no cuentan" in texto
