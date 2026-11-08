"""Tests de /sivendo."""

import pytest

from crypto_tracker.config import Posicion
from crypto_tracker.impuestos import Impuestos
from crypto_tracker.movimientos import MovimientoError
from crypto_tracker.sivendo import calcular, interpretar

BTC = Posicion("bitcoin", 0.02, 1000)


def _año(ganado=0.0, sin_datos=0):
    return Impuestos(2026, ganado, [], sin_datos, 1)


def _simula(dinero=700.0, ganado=0.0, antes=BTC, vendido=0.01):
    return calcular(antes, vendido, dinero, None, _año(ganado))


def test_ganancia_al_precio_medio():
    s = _simula()

    assert s.coste == pytest.approx(500)
    assert s.ganancia == pytest.approx(200)
    assert s.porcentaje == pytest.approx(40)
    assert s.hacienda == pytest.approx(38)


@pytest.mark.parametrize(
    "ganado, dinero, sale",
    [
        (5900, 700, 40),  # 100 al 19% y 100 al 21%
        (-100, 700, 19),  # las pérdidas de antes se restan
        (-500, 700, 0),  # y pueden taparla entera
        (1000, 300, -38),  # perder baja lo que ya ibas a pagar
        (0, 300, 0),  # sin ganancias que tapar no hay nada que bajar
    ],
)
def test_hacienda_sobre_lo_que_ya_llevas(ganado, dinero, sale):
    assert _simula(dinero, ganado).hacienda == pytest.approx(sale)


def test_sin_saber_lo_que_costo():
    s = _simula(antes=Posicion("bitcoin", 0.02, None))

    assert s.coste is None
    assert s.ganancia is None
    assert s.porcentaje is None
    assert s.hacienda is None


def test_gratis_no_da_porcentaje():
    s = _simula(antes=Posicion("bitcoin", 0.02, 0))

    assert s.ganancia == pytest.approx(700)
    assert s.porcentaje is None


def test_lo_que_queda():
    queda = Posicion("bitcoin", 0.015, 750)

    assert calcular(BTC, 0.005, 350, queda, _año()).queda == 0.015
    assert calcular(BTC, 0.02, 1400, None, _año()).queda == 0


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("btc 0.005", ("bitcoin", 0.005, None)),
        ("btc todo", ("bitcoin", None, None)),
        ("btc 0.005 @80000", ("bitcoin", 0.005, "@80000")),
        ("btc 0.005 400", ("bitcoin", 0.005, "400")),
    ],
)
def test_interpretar(texto, sale):
    assert interpretar(texto) == sale


@pytest.mark.parametrize(
    "texto", ["", "btc", "btc mucho", "btc 0", "btc 1 caro", "btc 1 2 3"]
)
def test_interpretar_mal_habla_de_sivendo(texto):
    with pytest.raises(MovimientoError, match="/sivendo"):
        interpretar(texto)
