"""Tests de /reparto."""

import pytest

from crypto_tracker.alerts import formatear_reparto
from crypto_tracker.cartera import Valor
from crypto_tracker.grafica import dibujar_reparto
from crypto_tracker.reparto import OTRAS, Trozo, trozos


def _valores(**valores):
    return [Valor(c, v, None, 1) for c, v in valores.items()]


def test_trozos_de_mas_a_menos_con_su_color():
    t = trozos(_valores(bitcoin=200, ethereum=600, solana=200))

    assert [x.coin_id for x in t] == ["ethereum", "bitcoin", "solana"]
    assert [x.peso for x in t] == [60, 20, 20]
    # El color sigue el orden de la cartera, no el tamaño
    assert [x.color for x in t] == [1, 0, 2]


def test_trozos_junta_las_pequeñas():
    t = trozos(_valores(a=100, b=90, c=80, d=70, e=60, f=50, g=40))

    assert [x.coin_id for x in t] == ["a", "b", "c", "d", "e", OTRAS]
    assert t[-1].valor == 90
    assert t[-1].color is None
    assert sum(x.peso for x in t) == pytest.approx(100)


def test_trozos_con_seis_no_junta_nada():
    t = trozos(_valores(a=6, b=5, c=4, d=3, e=2, f=1))

    assert OTRAS not in [x.coin_id for x in t]


def test_trozos_sin_valor():
    assert trozos([]) == []
    assert trozos(_valores(bitcoin=0)) == []
    assert [x.coin_id for x in trozos(_valores(a=10, b=0))] == ["a"]


def test_formatear():
    t = [Trozo("bitcoin", 1500, 75, 0), Trozo(OTRAS, 500, 25, None)]

    texto = formatear_reparto(t, 2000, "eur")

    assert "🥧 <b>Tu cartera</b>: €2.000,00" in texto
    assert "<b>Bitcoin</b> 75% · €1.500,00" in texto
    assert "<b>Otras</b> 25% · €500,00" in texto


@pytest.mark.parametrize("cuantas", [1, 3, 6])
def test_sale_un_png(cuantas):
    t = [Trozo(f"cripto-{i}", 10, 100 / cuantas, i) for i in range(cuantas)]

    assert dibujar_reparto(t, 10 * cuantas, "eur").startswith(b"\x89PNG")
