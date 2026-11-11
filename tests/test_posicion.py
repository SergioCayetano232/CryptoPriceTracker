"""Tests de /posicion."""

import pytest

from crypto_tracker.alerts import formatear_posicion
from crypto_tracker.posicion import (
    Entrada,
    Peticion,
    PosicionError,
    calcular,
    interpretar,
)


def test_cuanto_meter():
    e = calcular(Peticion(1000, 2, stop=10))

    assert e.dinero == pytest.approx(200)
    assert e.perdida == pytest.approx(20)
    assert not e.todo
    assert e.cantidad is None


def test_con_precio_da_la_cantidad_y_el_stop():
    e = calcular(Peticion(1000, 2, stop=10, coin_id="bitcoin"), 50000)

    assert e.cantidad == pytest.approx(0.004)
    assert e.precio_stop == pytest.approx(45000)


def test_stop_como_precio():
    e = calcular(Peticion(1000, 2, stop_precio=40000, coin_id="bitcoin"), 50000)

    assert e.stop == pytest.approx(20)
    assert e.dinero == pytest.approx(100)
    assert e.precio_stop == pytest.approx(40000)


def test_stop_por_encima_del_precio():
    with pytest.raises(PosicionError, match="por debajo"):
        calcular(Peticion(1000, 2, stop_precio=60000, coin_id="bitcoin"), 50000)


def test_stop_tan_cerca_que_va_todo():
    e = calcular(Peticion(1000, 2, stop=1))

    assert e.todo
    assert e.dinero == 1000
    assert e.perdida == pytest.approx(10)


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("1000 2% -10%", Peticion(1000, 2, stop=10)),
        ("1000 2% stop -10%", Peticion(1000, 2, stop=10)),
        ("1k 1,5% 5%", Peticion(1000, 1.5, stop=5)),
        ("1.000 € 2% -10%", Peticion(1000, 2, stop=10)),
        ("btc 1000 2% -10%", Peticion(1000, 2, stop=10, coin_id="bitcoin")),
        ("eth 1000 2% 2000", Peticion(1000, 2, stop_precio=2000, coin_id="ethereum")),
    ],
)
def test_interpretar(texto, esperado):
    assert interpretar(texto) == esperado


@pytest.mark.parametrize(
    "texto,error",
    [
        ("", "Escríbelo así"),
        ("1000 2%", "Escríbelo así"),
        ("mucho 2% -10%", "no es una cantidad"),
        ("1000 2 -10%", "en %"),
        ("1000 0% -10%", "en %"),
        ("1000 2% -100%", "entre 0% y 100%"),
        ("1000 2% 58000", "de qué cripto"),
        ("btc 1000 2% nada", "no es un stop"),
    ],
)
def test_interpretar_mal(texto, error):
    with pytest.raises(PosicionError, match=error):
        interpretar(texto)


def test_formatear():
    texto = formatear_posicion(Entrada(1000, 2, 10), "eur")

    assert texto.startswith("📐 <b>Cuánto meter</b>\n\n")
    assert "Con €1.000,00 y aceptando perder un 2%, mete <b>€200,00</b>" in texto
    assert "Si salta el stop (-10%), pierdes €20,00 y no más" in texto
    assert "Son" not in texto
    assert "comisiones" in texto


def test_formatear_con_cripto():
    texto = formatear_posicion(Entrada(1000, 2, 12.5, 64000.0, "bitcoin"), "eur")

    assert "Si salta el stop (-12,5%)" in texto
    assert "Son <b>0,0025 Bitcoin</b> a €64.000,00" in texto
    assert "el stop, a <b>€56.000,00</b>" in texto


def test_formatear_todo():
    texto = formatear_posicion(Entrada(1000, 2, 1), "eur")

    assert "puedes meter los <b>€1.000,00</b> enteros" in texto
    assert "pierdes €10,00, un 1%, dentro del 2% que aceptas" in texto
