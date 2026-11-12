"""Tests de /bollinger."""

from datetime import date, timedelta

import pytest

from crypto_tracker.alerts import formatear_bollinger
from crypto_tracker.bollinger import PERIODO, Bandas, calcular

INICIO = date(2026, 9, 1)


def _dias(precios, desde=INICIO):
    return [(desde + timedelta(days=i), p) for i, p in enumerate(precios)]


# Va y viene entre 95 y 105.
VAIVEN = [95.0, 105.0] * (PERIODO // 2)


def test_bandas():
    b = calcular(_dias(VAIVEN))

    assert b.media == pytest.approx(100)
    assert b.alta == pytest.approx(110)
    assert b.baja == pytest.approx(90)
    assert b.ancho == pytest.approx(20)
    assert b.zona == "dentro"
    assert b.posicion == pytest.approx(75)
    assert b.estrecha is None  # menos de un mes de anchos


def test_se_sale_por_arriba():
    b = calcular(_dias(VAIVEN[:-1] + [130.0]))

    assert b.zona == "encima"
    assert b.posicion > 100


def test_se_sale_por_abajo():
    assert calcular(_dias(VAIVEN[:-1] + [70.0])).zona == "debajo"


def test_estrecha():
    # Dos meses moviéndose mucho y los últimos 20 días casi quieta.
    movido = [80.0, 120.0] * 30
    quieto = [100.0, 100.5] * (PERIODO // 2)

    assert calcular(_dias(movido + quieto)).estrecha is True
    assert calcular(_dias(quieto + movido)).estrecha is False


def test_solo_el_ultimo_tramo_seguido():
    viejos = _dias(VAIVEN)
    nuevos = _dias(VAIVEN[:10], desde=INICIO + timedelta(days=40))
    assert calcular(viejos + nuevos) is None


def test_pocos_dias_o_plano():
    assert calcular(_dias(VAIVEN[:-1])) is None
    assert calcular(_dias([100.0] * PERIODO)) is None


def _bandas(ahora, estrecha=None):
    return Bandas(110.0, 100.0, 90.0, ahora, 20.0, estrecha, 25)


def test_formatear_dentro():
    texto = formatear_bollinger("bitcoin", _bandas(105.0), "eur")

    assert "📏 <b>Bitcoin</b>: bandas de Bollinger de 20 días" in texto
    assert "Banda alta: €110,00" in texto
    assert "Media: €100,00" in texto
    assert "Banda baja: €90,00" in texto
    assert "Está a <b>€105,00</b>, dentro de la banda" in texto
    assert "●" in texto


def test_formatear_encima():
    texto = formatear_bollinger("bitcoin", _bandas(115.0), "eur")
    assert "por encima de la banda alta: muy estirada" in texto


def test_formatear_debajo():
    texto = formatear_bollinger("bitcoin", _bandas(85.0), "eur")
    assert "por debajo de la banda baja: muy aplastada" in texto


def test_formatear_estrecha():
    texto = formatear_bollinger("bitcoin", _bandas(100.0, estrecha=True), "eur")
    assert "🤏 La banda está de las más estrechas" in texto
    assert "🤏" not in formatear_bollinger("bitcoin", _bandas(100.0, False), "eur")
