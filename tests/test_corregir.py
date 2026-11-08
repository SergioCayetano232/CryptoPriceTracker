"""Tests de /corregir."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.config import Posicion
from crypto_tracker.corregir import CANTIDAD, IMPORTE, calcular, interpretar
from crypto_tracker.ganancias import de_venta
from crypto_tracker.movimientos import Movimiento, MovimientoError

CUANDO = datetime(2026, 3, 1, 12, tzinfo=timezone.utc)
C = "bitcoin"


def _mov(id, tipo, cantidad, coste, antes):
    return Movimiento(id, C, tipo, cantidad, coste, antes, CUANDO)


# 1 BTC por 1.000, otro por 3.000 y se vende uno a medio de 2.000
HISTORIA = [
    _mov(1, "compra", 1, 1000, None),
    _mov(2, "compra", 1, 3000, Posicion(C, 1, 1000)),
    _mov(3, "venta", 1, 3000, Posicion(C, 2, 4000)),
]
ACTUAL = Posicion(C, 1, 2000)


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("12 cantidad 0.02", (12, CANTIDAD, "0.02")),
        ("#12 importe 700", (12, IMPORTE, "700")),
        ("12 IMPORTE @60000", (12, IMPORTE, "@60000")),
        ("12 coste 700", (12, IMPORTE, "700")),
    ],
)
def test_interpretar(texto, sale):
    assert interpretar(texto) == sale


@pytest.mark.parametrize(
    "texto",
    ["", "12", "12 importe", "doce importe 700", "12 importe 700 mas", "12 fecha 700"],
)
def test_interpretar_mal(texto):
    with pytest.raises(MovimientoError, match="/corregir 12"):
        interpretar(texto)


def test_importe_de_una_antigua_rehace_lo_de_detras():
    c = calcular(HISTORIA, 1, IMPORTE, "2000", ACTUAL)

    assert c.despues.coste == 2000
    assert c.historia[1].antes == Posicion(C, 1, 2000)
    assert c.historia[2].antes == Posicion(C, 2, 5000)
    assert c.final == Posicion(C, 1, 2500)
    assert c.rehechos == 2
    venta = c.historia[2]
    assert de_venta(venta.antes, venta.cantidad, venta.coste) == pytest.approx(500)


def test_cantidad():
    c = calcular(HISTORIA, 1, CANTIDAD, "2", ACTUAL)

    assert c.final.cantidad == pytest.approx(2)
    # Lo invertido no cambia al corregir cuántas: 4.000 entre 3, y se vende 1
    assert c.final.invertido == pytest.approx(4000 * 2 / 3)


def test_la_ultima_no_rehace_nada():
    c = calcular(HISTORIA, 3, IMPORTE, "3500", ACTUAL)

    assert c.rehechos == 0
    assert c.final == ACTUAL
    assert c.historia[2].coste == 3500


def test_importe_por_unidad():
    c = calcular(HISTORIA, 3, IMPORTE, "@3200", ACTUAL)

    assert c.despues.coste == pytest.approx(3200)


def test_una_venta_que_se_queda_sin_saldo_no_se_puede():
    lista = [
        _mov(1, "compra", 1, 1000, None),
        _mov(2, "venta", 1, 1500, Posicion(C, 1, 1000)),
    ]

    with pytest.raises(MovimientoError, match="la venta del 01/03/2026"):
        calcular(lista, 1, CANTIDAD, "0.5", None)


def test_corregir_la_venta_a_mas_de_lo_que_hay():
    with pytest.raises(MovimientoError, match="Así no cuadra"):
        calcular(HISTORIA, 3, CANTIDAD, "5", ACTUAL)


def test_vender_todo_y_recomprar():
    lista = [
        _mov(1, "compra", 1, 1000, None),
        _mov(2, "venta", 1, 1500, Posicion(C, 1, 1000)),
        _mov(3, "compra", 2, 4000, None),
    ]

    c = calcular(lista, 3, IMPORTE, "5000", Posicion(C, 2, 4000))

    assert c.final == Posicion(C, 2, 5000)


def test_con_lo_que_venia_del_env():
    env = Posicion(C, 0.5, 400)
    lista = [_mov(1, "compra", 0.5, 600, env)]

    c = calcular(lista, 1, IMPORTE, "800", Posicion(C, 1, 1000))

    assert c.historia[0].antes == env
    assert c.final == Posicion(C, 1, 1200)


def test_compra_sin_coste_sigue_sin_saberse():
    lista = [
        _mov(1, "compra", 1, None, None),
        _mov(2, "compra", 1, 500, Posicion(C, 1, None)),
    ]

    c = calcular(lista, 2, CANTIDAD, "2", Posicion(C, 2, None))

    assert c.final == Posicion(C, 3, None)


def test_recompensa_se_rehace_como_una_entrada():
    lista = [
        _mov(1, "compra", 1, 1000, None),
        _mov(2, "recompensa", 0.1, 200, Posicion(C, 1, 1000)),
    ]

    c = calcular(lista, 2, IMPORTE, "150", Posicion(C, 1.1, 1200))

    assert c.final.invertido == pytest.approx(1150)


def test_poner_el_importe_que_faltaba():
    lista = [
        _mov(1, "compra", 1, 1000, None),
        _mov(2, "venta", 0.5, None, Posicion(C, 1, 1000)),
    ]

    c = calcular(lista, 2, IMPORTE, "700", Posicion(C, 0.5, 500))

    venta = c.historia[1]
    assert de_venta(venta.antes, venta.cantidad, venta.coste) == pytest.approx(200)


def test_si_nada_cambia_lo_dice():
    with pytest.raises(MovimientoError, match="Ya está así"):
        calcular(HISTORIA, 1, IMPORTE, "1000", ACTUAL)


@pytest.mark.parametrize(
    "actual",
    [
        Posicion(C, 5, 2000),  # otra cantidad
        Posicion(C, 1, 9999),  # otro coste
        Posicion(C, 1, None),
        None,
    ],
)
def test_si_no_cuadra_no_toca(actual):
    with pytest.raises(MovimientoError, match="no cuadra con lo que tienes"):
        calcular(HISTORIA, 1, IMPORTE, "2000", actual)


def test_si_una_foto_intermedia_no_cuadra_no_toca():
    lista = [
        _mov(1, "compra", 1, 1000, None),
        _mov(2, "compra", 1, 3000, Posicion(C, 7, 1000)),
    ]

    with pytest.raises(MovimientoError, match="no cuadra"):
        calcular(lista, 1, IMPORTE, "2000", Posicion(C, 2, 4000))


@pytest.mark.parametrize(
    "campo, texto, mensaje",
    [
        (CANTIDAD, "0", "mayor que 0"),
        (CANTIDAD, "-1", "mayor que 0"),
        (CANTIDAD, "@5", "no me vale"),
        (CANTIDAD, "mucho", "no me vale"),
        (IMPORTE, "-5", "negativo"),
        (IMPORTE, "caro", "no me vale"),
    ],
)
def test_valores_malos(campo, texto, mensaje):
    with pytest.raises(MovimientoError, match=mensaje):
        calcular(HISTORIA, 1, campo, texto, ACTUAL)
