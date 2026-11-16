"""Tests de /permuta."""

import pytest

from crypto_tracker.comision import ComisionError
from crypto_tracker.config import Posicion
from crypto_tracker.impuestos import Impuestos
from crypto_tracker.movimientos import MovimientoError
from crypto_tracker.permuta import calcular, interpretar

BTC = Posicion("bitcoin", 0.02, 1000)


def _año(ganado=0.0):
    return Impuestos(2026, ganado, [], 0, 1)


def _permuta(texto_comision=None, ganado=0.0, antes=BTC):
    return calcular(
        antes, 0.01, 70000, "ethereum", 2000, None, _año(ganado), (), texto_comision
    )


def test_cuenta_como_vender():
    p = _permuta()

    assert p.recibes == pytest.approx(0.35)
    assert p.valor == pytest.approx(700)
    assert p.venta.coste == pytest.approx(500)
    assert p.venta.ganancia == pytest.approx(200)
    assert p.venta.hacienda == pytest.approx(38)


def test_la_comision_se_resta_de_lo_que_recibes():
    p = _permuta("1%")

    assert p.comision == pytest.approx(7)
    assert p.recibes == pytest.approx(0.3465)
    assert p.venta.ganancia == pytest.approx(193)


def test_comision_en_dinero():
    assert _permuta("5").comision == 5


def test_comision_mayor_que_lo_que_cambias():
    with pytest.raises(ComisionError):
        _permuta("800")


def test_suma_lo_que_ya_llevas():
    # 100 al 19% y 100 al 21%
    assert _permuta(ganado=5900).venta.hacienda == pytest.approx(40)


def test_sin_saber_lo_que_costo():
    p = _permuta(antes=Posicion("bitcoin", 0.02, None))

    assert p.recibes == pytest.approx(0.35)
    assert p.venta.hacienda is None


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("btc eth 0.01", ("bitcoin", "ethereum", 0.01, None)),
        ("btc eth todo", ("bitcoin", "ethereum", None, None)),
        ("bitcoin sol 0.01 com 0.1%", ("bitcoin", "solana", 0.01, "0.1%")),
        ("BTC ETH 0,01", ("bitcoin", "ethereum", 0.01, None)),
    ],
)
def test_interpretar(texto, sale):
    assert interpretar(texto) == sale


@pytest.mark.parametrize(
    "texto", ["", "btc eth", "btc 0.01", "btc eth 0.01 600", "btc eth x"]
)
def test_interpretar_mal_escrito(texto):
    with pytest.raises(MovimientoError, match="Escríbelo así"):
        interpretar(texto)


def test_por_ella_misma():
    with pytest.raises(MovimientoError, match="ella misma"):
        interpretar("btc bitcoin 0.01")
