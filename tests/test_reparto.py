"""Tests de /reparto."""

import pytest

from crypto_tracker.alerts import formatear_reparto
from crypto_tracker.cartera import Valor
from crypto_tracker.grafica import dibujar_reparto
from crypto_tracker.reparto import OTRAS, Trozo, demasiado, trozos


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


def test_demasiado_en_una():
    t = trozos(_valores(bitcoin=600, ethereum=300, solana=100))

    assert demasiado(t).coin_id == "bitcoin"


def test_justo_la_mitad_no_es_demasiado():
    assert demasiado(trozos(_valores(bitcoin=500, ethereum=500))) is None


def test_demasiado_con_una_sola_no_avisa():
    assert demasiado(trozos(_valores(bitcoin=500))) is None


def test_demasiado_no_cuenta_otras():
    t = [Trozo(OTRAS, 600, 60, None), Trozo("bitcoin", 400, 40, 0)]

    assert demasiado(t) is None


def test_formatear_avisa_si_una_es_mas_de_la_mitad():
    t = [Trozo("shiba-inu", 1500, 75, 0), Trozo("bitcoin", 500, 25, 1)]

    texto = formatear_reparto(t, 2000, "eur")

    assert texto.endswith(
        "\n\n⚖️ Más de la mitad es <b>Shiba Inu</b>. Si cae, lo notará toda la cartera."
    )


def test_formatear_repartida_no_avisa():
    t = [Trozo("bitcoin", 1000, 50, 0), Trozo("ethereum", 1000, 50, 1)]

    assert "⚖️" not in formatear_reparto(t, 2000, "eur")


@pytest.mark.parametrize("cuantas", [1, 3, 6])
def test_sale_un_png(cuantas):
    t = [Trozo(f"cripto-{i}", 10, 100 / cuantas, i) for i in range(cuantas)]

    assert dibujar_reparto(t, 10 * cuantas, "eur").startswith(b"\x89PNG")
