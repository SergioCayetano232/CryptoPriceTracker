"""Tests de /comisiones."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.alerts import formatear_comisiones
from crypto_tracker.comisiones import (
    Comisiones,
    ComisionesError,
    calcular,
    interpretar,
)
from crypto_tracker.movimientos import Movimiento


def _mov(id, coin, tipo, coste, comision, año=2026, nota=None):
    cuando = datetime(año, 6, 1, 12, tzinfo=timezone.utc)
    return Movimiento(id, coin, tipo, 0.01, coste, None, cuando, nota, comision)


LISTA = [
    # compra de 600 con 1,50 de comisión: coste 601,50
    _mov(1, "bitcoin", "compra", 601.5, 1.5, 2025),
    _mov(2, "ethereum", "compra", 202.0, 2.0),
    # venta de 400 con 4 de comisión: cobrado 396
    _mov(3, "bitcoin", "venta", 396.0, 4.0),
    _mov(4, "bitcoin", "compra", 500.0, None),
    _mov(5, "ethereum", "recompensa", 30.0, None),
]


@pytest.mark.parametrize("texto, esperado", [("", None), ("2025", 2025)])
def test_interpretar(texto, esperado):
    assert interpretar(texto, 2026) == esperado


@pytest.mark.parametrize("texto", ["2030", "1999", "ayer"])
def test_interpretar_mal(texto):
    with pytest.raises(ComisionesError):
        interpretar(texto, 2026)


def test_todas():
    c = calcular(LISTA)

    assert c.total == pytest.approx(7.5)
    assert c.movido == pytest.approx(600 + 200 + 400)
    assert c.porcentaje == pytest.approx(0.625)
    assert (c.con, c.sin) == (3, 1)
    assert c.por_año == {2026: 6.0, 2025: 1.5}
    assert list(c.por_cripto) == ["bitcoin", "ethereum"]
    assert c.por_cripto["bitcoin"] == pytest.approx(5.5)


def test_de_un_año():
    c = calcular(LISTA, 2025)

    assert c.total == pytest.approx(1.5)
    assert (c.con, c.sin) == (1, 0)
    assert c.por_año == {2025: 1.5}


def test_sin_ninguna():
    c = calcular([_mov(1, "bitcoin", "compra", 500.0, None)])

    assert c.total == 0
    assert c.porcentaje is None
    assert c.sin == 1


def test_venta_sin_lo_cobrado():
    c = calcular([_mov(1, "bitcoin", "venta", None, 2.0)])

    assert c.total == 2.0
    assert c.porcentaje is None


def test_formatear_todas():
    texto = formatear_comisiones(calcular(LISTA), "eur", None)

    assert "💸 <b>Tus comisiones</b>" in texto
    assert "Has pagado <b>€7,50</b> en 3 operaciones" in texto
    assert "un 0,62% de lo que moviste" in texto
    assert "2026: €6,00\n2025: €1,50" in texto
    assert "Bitcoin: €5,50\nEthereum: €2,00" in texto
    assert "1 compra o venta no lleva comisión apuntada" in texto


def test_formatear_un_año_no_repite_el_año():
    texto = formatear_comisiones(calcular(LISTA, 2025), "eur", 2025)

    assert "💸 <b>Tus comisiones de 2025</b>" in texto
    assert "en 1 operación" in texto
    assert "📅" not in texto
    assert "no lleva" not in texto


def test_formatear_sin_ninguna():
    c = Comisiones(0.0, 0.0, 0, 4, {}, {})
    texto = formatear_comisiones(c, "eur", None)

    assert "No tienes ninguna comisión apuntada" in texto
    assert "com 1.5" in texto
