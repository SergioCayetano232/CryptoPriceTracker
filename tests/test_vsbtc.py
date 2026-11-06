"""Tests de /vsbtc."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.alerts import formatear_vsbtc
from crypto_tracker.movimientos import Movimiento
from crypto_tracker.vsbtc import Contra, a_contar, calcular, cantidades, precio_en

INICIO = datetime(2026, 9, 1, 10, tzinfo=timezone.utc)


def _dia(n, horas=0):
    return INICIO + timedelta(days=n, hours=horas)


# bitcoin a 50.000 el día 0, a 40.000 el 10 y a 60.000 el 20
SERIE = [(_dia(0), 50000.0), (_dia(10), 40000.0), (_dia(20), 60000.0)]


def _mov(id, coin, tipo, cantidad, coste, dia):
    return Movimiento(id, coin, tipo, cantidad, coste, None, _dia(dia))


def test_precio_en_el_mas_cercano():
    assert precio_en(SERIE, _dia(10, horas=-3)) == 40000.0
    assert precio_en(SERIE, _dia(10, horas=5)) == 40000.0


def test_precio_en_muy_lejos():
    assert precio_en(SERIE, _dia(5)) is None
    assert precio_en([], _dia(0)) is None


def test_eth_contra_btc():
    # 1.000 € en ETH a 2.000 el día 0; hoy ETH a 3.000 y BTC a 60.000.
    r = calcular(
        [_mov(1, "ethereum", "compra", 0.5, 1000, 0)],
        SERIE,
        {"ethereum": 3000.0, "bitcoin": 60000.0},
    )

    assert r.real == 1500
    assert r.sats == pytest.approx(0.02)
    assert r.btc == pytest.approx(1200)
    assert r.diferencia == pytest.approx(300)
    assert r.ventaja == pytest.approx(25)
    assert r.contados == 1
    assert r.fuera == 0
    assert r.desde == _dia(0)


def test_una_venta_saca_lo_mismo_de_los_dos_lados():
    lista = [
        _mov(1, "ethereum", "compra", 1.0, 2000, 0),
        # vende la mitad por 800 € el día 10, con BTC a 40.000
        _mov(2, "ethereum", "venta", 0.5, 800, 10),
    ]
    r = calcular(lista, SERIE, {"ethereum": 3000.0, "bitcoin": 60000.0})

    assert r.real == 1500
    # 0,04 BTC comprados menos 0,02 vendidos
    assert r.sats == pytest.approx(0.02)
    assert r.btc == pytest.approx(1200)


def test_solo_bitcoin_sale_igual():
    r = calcular(
        [_mov(1, "bitcoin", "compra", 0.02, 1000, 0)],
        SERIE,
        {"bitcoin": 60000.0},
    )

    assert r.diferencia == pytest.approx(0)


def test_sin_precio_o_sin_btc_de_ese_dia_queda_fuera():
    lista = [
        _mov(1, "ethereum", "compra", 0.5, 1000, 0),
        _mov(2, "ethereum", "compra", 0.5, None, 10),
        _mov(3, "solana", "compra", 10, 1000, 5),
    ]
    r = calcular(lista, SERIE, {"ethereum": 3000.0, "bitcoin": 60000.0})

    assert r.contados == 1
    assert r.fuera == 2
    assert r.real == 1500


def test_venta_de_lo_del_env_no_deja_negativos():
    lista = [_mov(1, "ethereum", "venta", 1.0, 2000, 0)]

    assert cantidades(a_contar(lista, SERIE)) == {}
    r = calcular(lista, SERIE, {"bitcoin": 60000.0})
    assert r.sats == 0
    assert r.ventaja is None


def test_nada_que_comparar():
    assert calcular([], SERIE, {"bitcoin": 60000.0}) is None
    assert calcular([_mov(1, "ethereum", "compra", 1, 100, 5)], SERIE, {}) is None


def test_falta_el_precio_de_hoy():
    lista = [_mov(1, "ethereum", "compra", 0.5, 1000, 0)]

    assert calcular(lista, SERIE, {"bitcoin": 60000.0}) is None


def _contra(real, btc, fuera=0):
    return Contra(real, btc, btc / 60000, 3, fuera, INICIO)


def test_formatear_ganas_a_bitcoin():
    texto = formatear_vsbtc(_contra(1500, 1200), "eur")

    assert "<b>€1.500,00</b>" in texto
    assert "€1.200,00" in texto
    assert "0,02 BTC" in texto
    assert "Le ganas a bitcoin por <b>€300,00</b> (+25,0%)" in texto
    assert "01/09/2026" in texto


def test_formatear_pierdes():
    texto = formatear_vsbtc(_contra(900, 1200), "eur")

    assert "Bitcoin te gana por <b>€300,00</b> (-25,0%)" in texto


def test_formatear_empate():
    texto = formatear_vsbtc(_contra(1200, 1200), "eur")

    assert "Vas igual que bitcoin" in texto


def test_formatear_con_fuera():
    assert "2 movimientos no cuentan" in formatear_vsbtc(_contra(1, 1, fuera=2), "eur")
    assert "1 movimiento no cuenta" in formatear_vsbtc(_contra(1, 1, fuera=1), "eur")
