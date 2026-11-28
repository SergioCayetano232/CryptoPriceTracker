"""Tests de /timing."""

from datetime import date, datetime, timedelta, timezone

import pytest

from crypto_tracker.inversion.movimientos import Movimiento
from crypto_tracker.inversion.timing import a_mirar, calcular, dias_a_pedir, evaluar

# A mediodía: así la hora de aquí no cambia el día.
INICIO = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


def _mov(dia, coste, cantidad=1.0, tipo="compra", coin_id="bitcoin"):
    return Movimiento(
        dia, coin_id, tipo, cantidad, coste, None, INICIO + timedelta(days=dia)
    )


def _serie(precios):
    return [(INICIO + timedelta(days=i), p) for i, p in enumerate(precios)]


def _diarios(precios):
    return {(INICIO + timedelta(days=i)).date(): p for i, p in enumerate(precios)}


# Un mes en 100, con un bache a 80 el día 15.
PLANA = [100.0] * 15 + [80.0] + [100.0] * 15


def test_compra_en_el_bache():
    c = evaluar(_mov(15, 80), _diarios(PLANA))

    assert c.media == 100
    assert c.ahorro == pytest.approx(20)
    # El bache es su propio día: alrededor todo es 100, y 80 está por debajo.
    assert c.posicion is None


def test_compra_cara():
    precios = [90.0 + i for i in range(31)]  # sube un euro al día
    c = evaluar(_mov(15, 120), _diarios(precios))

    assert c.media == pytest.approx(105)
    assert c.ahorro == pytest.approx(-14.29, abs=0.01)
    assert c.posicion == 100  # por encima de todo lo de alrededor


def test_posicion_en_medio():
    precios = [90.0 + i for i in range(31)]
    c = evaluar(_mov(15, 105), _diarios(precios))

    assert c.posicion == pytest.approx(50)


def test_sin_coste_o_sin_dias_alrededor():
    assert evaluar(_mov(15, None), _diarios(PLANA)) is None
    # Solo 8 días guardados alrededor: no llega a MINIMO_DIAS.
    assert evaluar(_mov(15, 80), _diarios(PLANA[:8])) is None


def test_compra_reciente_con_la_ventana_a_medias():
    # Sin días después, pero con quince antes: vale.
    c = evaluar(_mov(30, 90), _diarios(PLANA))

    assert c is not None
    assert c.media == pytest.approx((100 * 14 + 80) / 15)


def test_calcular_pesa_por_lo_que_metiste():
    # Una grande en el bache y una pequeña cara.
    compras = [_mov(15, 800, cantidad=10), _mov(5, 110)]

    t = calcular(compras, {"bitcoin": _serie(PLANA)})

    assert t.baratas == 1
    assert t.mejor.movimiento.id == 15
    assert t.peor.movimiento.id == 5
    # Pagaste 910 por lo que a la media serían 10*100 + 1*~98,7
    assert t.ahorro == pytest.approx(17.2, abs=0.1)
    assert t.veredicto == "ojo"
    assert t.fuera == 0


def test_calcular_cuenta_las_que_no_puede():
    compras = [_mov(15, 80), _mov(15, 80, coin_id="pepe")]

    t = calcular(compras, {"bitcoin": _serie(PLANA)})

    assert len(t.compras) == 1
    assert t.fuera == 1


def test_calcular_sin_nada():
    assert calcular([_mov(15, 80)], {}) is None


@pytest.mark.parametrize("coste,veredicto", [(99.0, "azar"), (110.0, "caro")])
def test_veredicto(coste, veredicto):
    t = calcular([_mov(5, coste)], {"bitcoin": _serie([100.0] * 31)})

    assert t.veredicto == veredicto


def test_a_mirar_solo_compras():
    assert [m.tipo for m in a_mirar([_mov(1, 1), _mov(2, 1, tipo="venta")])] == [
        "compra"
    ]


def test_dias_a_pedir():
    compras = [_mov(0, 1), _mov(10, 1)]

    assert dias_a_pedir(compras, date(2026, 10, 1)) == 30 + 15 + 1
    assert dias_a_pedir(compras, date(2028, 1, 1)) == 365
