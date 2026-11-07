"""Tests de la nota de /compra y /venta."""

import pytest

from crypto_tracker.movimientos import MovimientoError
from crypto_tracker.nota import separar


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("btc 0.01 600 por el halving", ("btc 0.01 600", "por el halving")),
        ("btc 0.01 @60000 dip", ("btc 0.01 @60000", "dip")),
        (
            "btc 0.01 600 com 1,5 por el halving",
            ("btc 0.01 600 com 1,5", "por el halving"),
        ),
        ("btc 0.01 por el halving", ("btc 0.01", "por el halving")),
        ("btc 0.01 com 1 dip", ("btc 0.01 com 1", "dip")),
        ("btc todo para el coche", ("btc todo", "para el coche")),
        ("btc 0.01 600", ("btc 0.01 600", None)),
        ("btc 0.01 600 com 1", ("btc 0.01 600 com 1", None)),
        ("btc 0.01", ("btc 0.01", None)),
        ("btc", ("btc", None)),
    ],
)
def test_separar(texto, sale):
    assert separar(texto) == sale


def test_com_sin_numero_no_se_toma_por_nota():
    # Así comision.separar avisa de que falta el número
    assert separar("btc 0.01 600 com") == ("btc 0.01 600 com", None)


def test_nota_muy_larga():
    with pytest.raises(MovimientoError, match="muy larga"):
        separar("btc 0.01 600 " + "a" * 101)
