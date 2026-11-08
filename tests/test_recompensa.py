"""Tests de las recompensas: que no se cuelen como compras ni como ventas."""

from datetime import date, datetime, timedelta, timezone

import pytest

from crypto_tracker import hodl, rentabilidad, vsbtc
from crypto_tracker.alerts import formatear_impuestos, formatear_movimientos
from crypto_tracker.compras import calcular as calcular_compras
from crypto_tracker.config import Posicion
from crypto_tracker.impuestos import Impuestos, recompensas_de
from crypto_tracker.movimientos import (
    Movimiento,
    MovimientoError,
    interpretar_recompensa,
    recibido,
    totales,
)

T0 = datetime(2026, 3, 1, 12, tzinfo=timezone.utc)
SERIE = [(T0 + timedelta(days=d), 50000.0) for d in range(40)]


def _mov(id, tipo, cantidad, coste, dias=0, coin_id="ethereum", antes=None):
    return Movimiento(
        id, coin_id, tipo, cantidad, coste, antes, T0 + timedelta(days=dias)
    )


LISTA = [
    _mov(1, "compra", 0.5, 1000),
    _mov(2, "recompensa", 0.1, 200, 5, antes=Posicion("ethereum", 0.5, 1000)),
]


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("eth 0.02", ("ethereum", 0.02, None)),
        ("eth 0.02 50", ("ethereum", 0.02, 50)),
        ("eth 0.02 @2500", ("ethereum", 0.02, 50)),
        ("eth 0.02 0", ("ethereum", 0.02, 0)),
    ],
)
def test_interpretar(texto, sale):
    coin_id, cantidad, valor = interpretar_recompensa(texto)

    assert (coin_id, cantidad) == sale[:2]
    assert valor == pytest.approx(sale[2]) if sale[2] is not None else valor is None


@pytest.mark.parametrize("texto", ["", "eth", "eth mucho", "eth 0", "eth 1 -5"])
def test_interpretar_mal_habla_de_recompensa(texto):
    with pytest.raises(MovimientoError, match="/recompensa"):
        interpretar_recompensa(texto)


def test_recibido_y_totales_van_aparte():
    assert recibido(LISTA) == 200
    assert totales(LISTA) == (1000, 0)


def test_recompensas_solo_del_año():
    lista = [*LISTA, _mov(3, "recompensa", 1, 70, 400)]  # ya es 2027

    assert recompensas_de(lista, 2026) == 200
    assert recompensas_de(lista, 2027) == 70
    assert recompensas_de(lista, 2020) == 0


def test_rentabilidad_no_la_cuenta_como_dinero():
    ahora = T0 + timedelta(days=60)

    r = rentabilidad.calcular(LISTA, {"ethereum": 2000.0}, ahora)

    assert r.metido == 1000
    assert r.sacado == 0
    assert r.vale == pytest.approx(1200)  # 0,6 a 2.000: la recompensa sí vale
    assert r.ganancia == pytest.approx(200)
    assert r.fuera == 0
    assert r.anual is not None


def test_rentabilidad_se_puede_vender_lo_recibido():
    lista = [*LISTA, _mov(3, "venta", 0.6, 1500, 10)]

    dentro, tienes = rentabilidad.contables(lista)

    assert [m.id for m in dentro] == [1, 3]
    assert tienes == {}


def test_rentabilidad_recompensa_sin_valor_sigue_sumando():
    lista = [*LISTA, _mov(3, "recompensa", 0.4, 0, 6)]

    _, tienes = rentabilidad.contables(lista)

    assert tienes["ethereum"] == pytest.approx(1.0)


def test_vsbtc_suma_en_lo_real_y_no_en_bitcoin():
    r = vsbtc.calcular(LISTA, SERIE, {"ethereum": 2000.0, "bitcoin": 50000.0})

    assert r.sats == pytest.approx(0.02)
    assert r.btc == pytest.approx(1000)
    assert r.real == pytest.approx(1200)


def test_vsbtc_solo_con_recompensas_no_hay_nada_que_comparar():
    assert vsbtc.a_contar([LISTA[1]], SERIE) == []


def test_hodl_cuenta_desde_la_recompensa():
    lista = [_mov(1, "recompensa", 1, 10)]

    [h], _ = hodl.calcular([Posicion("ethereum", 1, 10)], lista, date(2026, 3, 11))

    assert h.desde == T0


def test_compras_no_la_cuenta():
    r = calcular_compras(LISTA, {"ethereum": 3000.0})

    assert r.total == 1


def test_movimientos_la_enseña_como_recompensa():
    texto = formatear_movimientos(list(reversed(LISTA)), "eur")

    assert "🎁 Recompensa de 0,1 de Ethereum que valía €200,00" in texto
    assert "Venta" not in texto
    assert "€1.000,00 comprado" in texto
    assert "🎁 €200,00 en recompensas" in texto


def test_impuestos_avisa_de_las_recompensas():
    texto = formatear_impuestos(Impuestos(2026, 100, [], 0, 1), "eur", 200.0)

    assert "Recibiste €200,00 en recompensas" in texto


def test_impuestos_sin_ventas_no_dice_que_no_hay_nada():
    texto = formatear_impuestos(Impuestos(2026, 0, [], 0, 0), "eur", 200.0)

    assert "nada que declarar" not in texto
    assert "Recibiste €200,00" in texto


def test_impuestos_sin_recompensas_no_las_menciona():
    assert "recompensas" not in formatear_impuestos(
        Impuestos(2026, 100, [], 0, 1), "eur"
    )
