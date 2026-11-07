"""Tests del resumen del año."""

from datetime import date, datetime, time, timedelta

import pytest

from crypto_tracker.anual import AnualError, calcular, interpretar, meses, toca, tramo
from crypto_tracker.config import Posicion
from crypto_tracker.movimientos import Movimiento

POSICIONES = [Posicion("bitcoin", 0.1, 5000), Posicion("solana", 10, 1000)]


def _dia(mes, dia, hora=12):
    return datetime(2025, mes, dia, hora).astimezone()


def _filas(*precios):
    """(mes, dia, btc, sol) -> las filas de get_series."""
    filas = []
    for mes, dia, btc, sol in precios:
        filas += [(_dia(mes, dia), "bitcoin", btc), (_dia(mes, dia), "solana", sol)]
    return filas


def _mov(id, coin, tipo, cantidad, coste, mes, antes=None, año=2025):
    cuando = datetime(año, mes, 10, 10).astimezone()
    return Movimiento(id, coin, tipo, cantidad, coste, antes, cuando)


FILAS = _filas(
    (1, 2, 50000, 100),  # 5.000 + 1.000 = 6.000
    (1, 30, 55000, 100),  # 6.500: enero +8,3%
    (3, 1, 55000, 120),  # 6.700
    (3, 31, 44000, 120),  # 5.600: marzo -16,4%
    (12, 31, 66000, 150),  # 8.100
)


def test_toca_el_1_de_enero():
    uno = datetime(2026, 1, 1, 9, 5).astimezone()

    assert toca(uno, time(9, 0), None)
    assert not toca(uno, time(9, 0), uno.date())
    assert not toca(uno + timedelta(days=1), time(9, 0), None)
    assert not toca(datetime(2026, 2, 1, 9, 5).astimezone(), time(9, 0), None)


@pytest.mark.parametrize("texto, sale", [("2025", 2025), (" 2026 ", 2026)])
def test_interpretar(texto, sale):
    assert interpretar(texto, 2026) == sale


@pytest.mark.parametrize("texto", ["", "2027", "2008", "el pasado"])
def test_interpretar_mal(texto):
    with pytest.raises(AnualError, match="entre 2009 y 2026"):
        interpretar(texto, 2026)


def test_tramo():
    desde, hasta = tramo(2025)

    assert (desde.year, desde.month, desde.day, desde.hour) == (2025, 1, 1, 0)
    assert (hasta.year, hasta.month, hasta.day) == (2026, 1, 1)


def test_meses():
    serie = [
        (_dia(1, 2), 100.0),
        (_dia(1, 30), 110.0),
        (_dia(2, 15), 50.0),  # un solo precio: no se puede decir nada
        (_dia(3, 1), 100.0),
        (_dia(3, 31), 90.0),
    ]

    assert meses(serie) == [(1, pytest.approx(10)), (3, pytest.approx(-10))]


def test_la_cartera_y_sus_meses():
    a = calcular(2025, POSICIONES, FILAS, [])

    assert a.cartera.inicio == 6000
    assert a.cartera.fin == 8100
    assert a.cartera.cambios[0] == ("solana", pytest.approx(50))
    assert a.mejor_mes == (1, pytest.approx(500 / 6000 * 100))
    assert a.peor_mes == (3, pytest.approx(-1100 / 6700 * 100))
    assert a.desde == date(2025, 1, 2)


def test_compras_y_ventas_del_año():
    antes = Posicion("bitcoin", 0.02, 1000)
    lista = [
        _mov(1, "bitcoin", "compra", 0.01, 400, 2),  # a 40.000: +65% a fin de año
        _mov(2, "solana", "compra", 2, 300, 5),  # a 150: igual
        _mov(3, "bitcoin", "venta", 0.01, 700, 6, antes),  # costaron 500
        _mov(4, "bitcoin", "compra", 1, 1, 3, año=2024),  # de otro año
    ]

    a = calcular(2025, POSICIONES, FILAS, lista)

    assert (a.compras, a.comprado) == (2, 700)
    assert (a.ventas, a.vendido) == (1, 700)
    assert a.ganado == pytest.approx(200)
    # Al último precio del año, no al de hoy
    assert a.mis_compras.mejor.movimiento.id == 1
    assert a.mis_compras.mejor.precio == 66000
    assert a.mis_compras.peor.movimiento.id == 2


def test_sin_precios_ni_movimientos():
    a = calcular(2025, POSICIONES, [], [])

    assert a.cartera is None
    assert a.meses == [] and a.mejor_mes is None and a.desde is None
    assert (a.compras, a.ventas, a.ganado) == (0, 0, 0)
    assert a.mis_compras is None


def test_con_un_solo_mes_no_hay_mejor_ni_peor():
    a = calcular(2025, POSICIONES, _filas((12, 1, 1, 1), (12, 31, 2, 2)), [])

    assert a.mejor_mes is None and a.peor_mes is None


def _texto(a, hoy=date(2026, 1, 1)):
    from crypto_tracker.alerts import formatear_anual

    return formatear_anual(a, "eur", hoy)


def test_formatear():
    antes = Posicion("bitcoin", 0.02, 1000)
    lista = [
        _mov(1, "bitcoin", "compra", 0.01, 400, 2),
        _mov(2, "solana", "compra", 2, 300, 5),
        _mov(3, "bitcoin", "venta", 0.01, 700, 6, antes),
    ]
    texto = _texto(calcular(2025, POSICIONES, FILAS, lista))

    assert "🎆 <b>Tu 2025 en cripto</b>" in texto
    assert "de €6.000,00 a <b>€8.100,00</b> 🔺 +35,0% (+€2.100,00)" in texto
    assert "La que mejor, Solana: +50,0%. La que peor, Bitcoin: +32,0%" in texto
    assert "Mejor mes, enero: +8,3%. Peor, marzo: -16,4%" in texto
    assert "🛒 2 compras por €700,00 · 💸 1 venta por €700,00" in texto
    assert "💰 Vendiendo, +€200,00. El detalle, en /impuestos 2025" in texto
    assert "⭐ Tu mejor compra: 0,01 de Bitcoin el 10/02, 🔺 +65,0%, a fin de año" in (
        texto
    )
    assert "🥴 La peor: 2 de Solana el 10/05, ➖ +0,0%" in texto
    assert "Solo tengo precios" not in texto


def test_formatear_el_año_en_curso():
    texto = _texto(calcular(2025, POSICIONES, FILAS, []), hoy=date(2025, 12, 31))

    assert "Tu 2025 en cripto hasta hoy" in texto


def test_formatear_sin_el_principio_del_año():
    filas = _filas((10, 15, 50000, 100), (12, 31, 66000, 150))

    texto = _texto(calcular(2025, POSICIONES, filas, []))

    assert "Solo tengo precios desde el 15/10. Para guardar el año entero" in texto


def test_formatear_solo_movimientos():
    lista = [_mov(1, "bitcoin", "compra", 0.01, 400, 2)]

    texto = _texto(calcular(2025, POSICIONES, [], lista))

    assert "🛒 1 compra por €400,00 · 💸 0 ventas" in texto
    assert "Tu cartera" not in texto
    assert "Vendiendo" not in texto


def test_formatear_nada():
    texto = _texto(calcular(2025, POSICIONES, [], []))

    assert texto.startswith("De 2025 no tengo nada")
