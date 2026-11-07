"""Tests de la comisión de /compra y /venta."""

import pytest

from crypto_tracker.comision import ComisionError, calcular, de_venta, separar
from crypto_tracker.movimientos import MovimientoError


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("btc 0.01 600 com 1.5", ("btc 0.01 600", "1.5")),
        ("btc 0.01 @60000 fee 0.1%", ("btc 0.01 @60000", "0.1%")),
        ("btc 0.01 Comisión 2", ("btc 0.01", "2")),
        ("btc todo com 1", ("btc todo", "1")),
        ("btc 0.01 600", ("btc 0.01 600", None)),
    ],
)
def test_separar(texto, sale):
    assert separar(texto) == sale


@pytest.mark.parametrize("texto", ["btc 0.01 com", "btc com 1 600"])
def test_separar_mal_puesta(texto):
    with pytest.raises(ComisionError, match="va al final"):
        separar(texto)


@pytest.mark.parametrize(
    "texto, importe, sale",
    [("1.5", 600, 1.5), ("1,5", 600, 1.5), ("0.1%", 600, 0.6), ("0", 600, 0)],
)
def test_calcular(texto, importe, sale):
    assert calcular(texto, importe) == pytest.approx(sale)


@pytest.mark.parametrize(
    "texto, error", [("abc", "no es una comisión"), ("100%", "100 %")]
)
def test_calcular_mal(texto, error):
    with pytest.raises(ComisionError, match=error):
        calcular(texto, 600)


def test_de_venta():
    assert de_venta(700, 2) == 698


def test_de_venta_mayor_que_lo_cobrado():
    with pytest.raises(ComisionError, match="más que lo que te dieron"):
        de_venta(1, 2)


def test_es_un_error_de_movimiento():
    # /compra y /venta solo cogen MovimientoError
    assert issubclass(ComisionError, MovimientoError)
