"""Tests de /hodl."""

from datetime import date, datetime, timezone

from crypto_tracker.alerts import formatear_hodl
from crypto_tracker.config import Posicion
from crypto_tracker.hodl import Hodl, calcular
from crypto_tracker.movimientos import Movimiento

HOY = date(2026, 11, 5)


def _dia(mes, dia):
    return datetime(2026, mes, dia, 12, tzinfo=timezone.utc)


def _mov(id, tipo, cantidad, antes, cuando, coin_id="bitcoin"):
    previa = Posicion(coin_id, antes) if antes is not None else None
    return Movimiento(id, coin_id, tipo, cantidad, None, previa, cuando)


def test_desde_la_primera_compra():
    movs = [
        _mov(1, "compra", 0.01, None, _dia(3, 1)),
        _mov(2, "compra", 0.01, 0.01, _dia(6, 1)),
    ]

    [h], _ = calcular([Posicion("bitcoin", 0.02)], movs, HOY)

    assert h.desde == _dia(3, 1)
    assert not h.venta and not h.minimo
    assert h.dias(HOY) == 249


def test_desde_la_ultima_venta():
    movs = [
        _mov(1, "compra", 0.02, None, _dia(3, 1)),
        _mov(2, "venta", 0.005, 0.02, _dia(8, 1)),
        _mov(3, "venta", 0.005, 0.015, _dia(10, 1)),
    ]

    [h], _ = calcular([Posicion("bitcoin", 0.01)], movs, HOY)

    assert h.desde == _dia(10, 1)
    assert h.venta


def test_si_lo_vendiste_todo_empieza_en_la_siguiente_compra():
    movs = [
        _mov(1, "compra", 0.01, None, _dia(1, 10)),
        _mov(2, "venta", 0.01, 0.01, _dia(4, 1)),
        _mov(3, "compra", 0.02, None, _dia(9, 15)),
    ]

    [h], _ = calcular([Posicion("bitcoin", 0.02)], movs, HOY)

    assert h.desde == _dia(9, 15)
    assert not h.venta and not h.minimo


def test_ya_la_tenias_en_el_env():
    movs = [_mov(1, "compra", 0.01, 0.05, _dia(9, 1))]

    [h], _ = calcular([Posicion("bitcoin", 0.06)], movs, HOY)

    assert h.minimo


def test_sin_movimientos_no_hay_fecha():
    lista, sin_fecha = calcular([Posicion("solana", 3)], [], HOY)

    assert lista == []
    assert sin_fecha == ["solana"]


def test_las_que_ya_no_tienes_no_salen():
    movs = [
        _mov(1, "compra", 1, None, _dia(1, 10), "ethereum"),
        _mov(2, "venta", 1, 1, _dia(4, 1), "ethereum"),
    ]

    lista, sin_fecha = calcular([Posicion("ethereum", 0)], movs, HOY)

    assert lista == [] and sin_fecha == []


def test_de_la_que_mas_lleva_a_la_que_menos():
    movs = [
        _mov(1, "compra", 1, None, _dia(10, 1), "solana"),
        _mov(2, "compra", 0.01, None, _dia(2, 1)),
    ]

    lista, _ = calcular([Posicion("solana", 1), Posicion("bitcoin", 0.01)], movs, HOY)

    assert [h.coin_id for h in lista] == ["bitcoin", "solana"]


def test_formatear():
    lista = [
        Hodl("bitcoin", _dia(3, 1), False),
        Hodl("solana", _dia(10, 1), True),
        Hodl("ethereum", _dia(11, 4), False, minimo=True),
        Hodl("cardano", _dia(11, 5), False),
    ]

    texto = formatear_hodl(lista, ["polkadot"], HOY)

    assert "💎 <b>Lo que llevas sin vender</b>" in texto
    assert "<b>Bitcoin</b>  249 días" in texto
    assert "desde la compra del 01/03/2026" in texto
    assert "<b>Solana</b>  35 días" in texto
    assert "desde que vendiste un poco el 01/10/2026" in texto
    assert "<b>Ethereum</b>  más de 1 día" in texto
    assert "ya la tenías antes de apuntar la compra del 04/11/2026" in texto
    assert "<b>Cardano</b>  hoy" in texto
    assert "De Polkadot no sé desde cuándo" in texto


def test_formatear_miles():
    texto = formatear_hodl(
        [Hodl("bitcoin", _dia(1, 1).replace(year=2023), False)], [], HOY
    )

    assert "1.404 días" in texto
