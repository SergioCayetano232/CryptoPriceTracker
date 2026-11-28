"""Tests de la tarjeta de /anual."""

from datetime import date, datetime

import pytest

from crypto_tracker.config import Posicion
from crypto_tracker.informes.anual import calcular as calcular_año
from crypto_tracker.informes.tarjeta_anual import calcular, pedida
from crypto_tracker.movimientos import Movimiento

POSICIONES = [Posicion("bitcoin", 0.1, 5000), Posicion("solana", 10, 1000)]


def _filas(*precios):
    """(mes, dia, btc, sol) -> las filas de get_series."""
    filas = []
    for mes, dia, btc, sol in precios:
        cuando = datetime(2025, mes, dia, 12).astimezone()
        filas += [(cuando, "bitcoin", btc), (cuando, "solana", sol)]
    return filas


def _mov(id, coin, cantidad, coste, mes):
    cuando = datetime(2025, mes, 10, 10).astimezone()
    return Movimiento(id, coin, "compra", cantidad, coste, None, cuando)


FILAS = _filas(
    (1, 2, 50000, 100),  # 6.000
    (1, 30, 55000, 100),  # 6.500: enero +8,3%
    (3, 1, 55000, 120),  # 6.700
    (3, 31, 44000, 120),  # 5.600: marzo -16,4%
    (12, 31, 66000, 150),  # 8.100
)


@pytest.mark.parametrize(
    "texto, sale",
    [
        ("", (False, "")),
        ("2025", (False, "2025")),
        ("tarjeta", (True, "")),
        ("2025 tarjeta", (True, "2025")),
        ("Tarjeta 2025", (True, "2025")),
    ],
)
def test_pedida(texto, sale):
    assert pedida(texto) == sale


def test_calcular_con_todo():
    compras = [
        _mov(1, "bitcoin", 0.01, 400, 2),  # a 40.000: +65% a fin de año
        _mov(2, "solana", 2, 300, 5),  # a 150: igual
    ]
    a = calcular_año(2025, POSICIONES, FILAS, compras)

    t = calcular(a, date(2026, 1, 1))

    assert t.año == 2025
    assert t.hasta is None
    assert t.desde is None
    assert t.total == pytest.approx(35)  # de 6.000 a 8.100
    # Diciembre no sale: con un solo precio no hay mes que medir.
    assert t.meses == {
        1: pytest.approx(500 / 6000 * 100),
        3: pytest.approx(-1100 / 6700 * 100),
    }
    assert t.mejor == ("solana", pytest.approx(50))
    assert t.mejor_mes[0] == 1
    assert (t.compras, t.ventas) == (2, 0)
    assert t.mejor_compra == ("bitcoin", pytest.approx(65))
    # Como en /compras, la que se queda igual cuenta como verde.
    assert (t.verdes, t.juzgadas) == (2, 2)


def test_calcular_el_año_en_curso_lleva_hasta_cuando():
    a = calcular_año(2025, POSICIONES, FILAS, [])

    assert calcular(a, date(2025, 11, 23)).hasta == date(2025, 11, 23)


def test_calcular_con_precios_desde_medio_año():
    tarde = _filas((10, 5, 50000, 100), (11, 20, 40000, 90))

    t = calcular(calcular_año(2025, POSICIONES, tarde, []), date(2026, 1, 1))

    assert t.desde == date(2025, 10, 5)


def test_calcular_sin_precios_de_ese_año():
    # Con compras pero sin precios no hay ni % ni con qué juzgarlas.
    a = calcular_año(2025, POSICIONES, [], [_mov(1, "bitcoin", 0.01, 400, 2)])

    assert calcular(a, date(2026, 1, 1)) is None


def test_calcular_con_compras_y_sin_cartera_que_se_mueva():
    plano = _filas((5, 1, 50000, 100), (5, 30, 50000, 100))
    a = calcular_año(2025, POSICIONES, plano, [_mov(1, "bitcoin", 0.01, 400, 2)])

    t = calcular(a, date(2026, 1, 1))

    assert t.total is None
    assert t.mejor_compra == ("bitcoin", pytest.approx(25))


def test_calcular_sin_nada_que_enseñar():
    assert calcular(calcular_año(2025, POSICIONES, [], []), date(2026, 1, 1)) is None


def test_calcular_con_todo_plano():
    plano = _filas((5, 1, 50000, 100), (5, 30, 50000, 100))

    assert calcular(calcular_año(2025, POSICIONES, plano, []), date(2026, 1, 1)) is None
