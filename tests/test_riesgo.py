"""Tests de /riesgo."""

from datetime import date

import pytest

from crypto_tracker.alerts import formatear_riesgo
from crypto_tracker.cartera import Valor
from crypto_tracker.riesgo import Riesgo, calcular
from crypto_tracker.volatilidad import Volatilidad

PEOR = date(2026, 10, 12)


def _valores(**cuanto):
    return [Valor(c, v) for c, v in cuanto.items()]


def _mov(media, peor=-6.3):
    return Volatilidad(media, peor, PEOR, 29)


def test_concentracion():
    r = calcular(_valores(bitcoin=8000, ethereum=1000, solana=1000), _mov(2.0), 1.8)

    assert r.total == 10000
    assert r.mayor == "bitcoin"
    assert r.peso == pytest.approx(80)
    assert r.equivalentes == pytest.approx(1 / (0.64 + 0.01 + 0.01))
    assert r.cuantas == 3
    assert r.si_cae == pytest.approx(16)


def test_a_partes_iguales_equivale_a_las_que_tienes():
    r = calcular(_valores(bitcoin=100, ethereum=100, solana=100), None, None)

    assert r.equivalentes == pytest.approx(3)


def test_lo_que_no_vale_nada_no_cuenta():
    r = calcular(_valores(bitcoin=1000, shiba=0), None, None)

    assert r.cuantas == 1
    assert r.peso == 100


def test_movimiento():
    r = calcular(_valores(bitcoin=5000, ethereum=5000), _mov(2.0), 1.8)

    assert r.al_dia == pytest.approx(200)
    assert r.nivel == "medio"


@pytest.mark.parametrize(
    "media, nivel", [(1.0, "bajo"), (1.5, "medio"), (3.4, "medio"), (3.5, "alto")]
)
def test_nivel(media, nivel):
    assert calcular(_valores(bitcoin=1), _mov(media), None).nivel == nivel


@pytest.mark.parametrize(
    "media, btc, sale",
    [(3.0, 2.0, "más"), (1.7, 2.0, "menos"), (2.1, 2.0, "igual"), (2.0, None, None)],
)
def test_contra_btc(media, btc, sale):
    r = calcular(_valores(bitcoin=5000, solana=5000), _mov(media), btc)

    assert r.contra_btc == sale


def test_solo_bitcoin_no_se_compara_con_bitcoin():
    r = calcular(_valores(bitcoin=5000), _mov(2.0), 2.0)

    assert r.contra_btc is None


def test_sin_precios_guardados():
    r = calcular(_valores(bitcoin=5000), None, None)

    assert r.al_dia is None and r.nivel is None and r.contra_btc is None


def test_cartera_sin_valor():
    assert calcular([], None, None) is None


def _r(**cambios):
    datos = dict(
        total=10000.0,
        mayor="bitcoin",
        peso=80.0,
        equivalentes=1.52,
        cuantas=3,
        movimiento=_mov(2.0),
        btc=1.9,
    )
    return Riesgo(**{**datos, **cambios})


def test_formatear():
    texto = formatear_riesgo(_r(), "eur")

    assert "🎯 <b>El riesgo de tu cartera</b>" in texto
    assert "<b>Bitcoin</b> es el 80% de lo que tienes" in texto
    assert "si cae un 20%, tu cartera cae un 16%" in texto
    assert "Con 3 criptos, es como tener 1,5 a partes iguales" in texto
    assert "Se mueve de media un 2,0% al día: unos <b>€200,00</b>" in texto
    assert "Su día más movido, el 12/10: 🔻 -6,3%" in texto
    assert "Se mueve igual que bitcoin (1,9%)" in texto
    assert "🟠 Riesgo medio" in texto


def test_formatear_mas_que_bitcoin_y_alto():
    texto = formatear_riesgo(_r(movimiento=_mov(4.0), btc=2.0), "eur")

    assert "Se mueve más que bitcoin (2,0%)" in texto
    assert "🔴 Riesgo alto" in texto


def test_formatear_una_sola():
    texto = formatear_riesgo(_r(peso=100.0, cuantas=1, equivalentes=1.0), "eur")

    assert "Todo lo que tienes es <b>Bitcoin</b>" in texto
    assert "a partes iguales" not in texto


def test_formatear_bien_repartida():
    texto = formatear_riesgo(
        _r(peso=34.0, equivalentes=2.99, movimiento=_mov(1.0)), "eur"
    )

    assert "Con 3 criptos, es como tener 3 a partes iguales" in texto
    assert "🟢 Riesgo bajo" in texto


def test_formatear_sin_precios_guardados():
    texto = formatear_riesgo(_r(movimiento=None), "eur")

    assert "Aún no tengo dos días de precios de tu cartera" in texto
    assert "Riesgo" not in texto.split("\n", 1)[1]
