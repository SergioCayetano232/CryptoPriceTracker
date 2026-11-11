"""Tests del aviso de cruce de medias."""

from datetime import date, timedelta

import pytest

from crypto_tracker.alerts import formatear_cruce
from crypto_tracker.cruce import ABAJO, ARRIBA, Cruce, apuntar, calcular, toca


def _dias(precios):
    primero = date(2026, 11, 11) - timedelta(days=len(precios) - 1)
    return [(primero + timedelta(days=i), p) for i, p in enumerate(precios)]


def test_la_corta_por_encima():
    c = calcular("bitcoin", _dias([100.0] * 160 + [110.0] * 50), 110.0)

    assert c.corta == pytest.approx(110)
    assert c.larga == pytest.approx(102.5)
    assert c.lado == ARRIBA


def test_la_corta_por_debajo():
    c = calcular("bitcoin", _dias([100.0] * 160 + [90.0] * 50), 90.0)

    assert c.lado == ABAJO


def test_casi_iguales_no_se_sabe():
    c = calcular("bitcoin", _dias([100.0] * 160 + [100.4] * 50), 100.4)

    assert c.lado is None


def test_sin_200_dias_no_hay_cruce():
    assert calcular("bitcoin", _dias([100.0] * 120), 100.0) is None


def test_la_primera_vez_solo_se_apunta():
    c = Cruce("bitcoin", 110.0, 100.0, 110.0)

    assert not toca(c, None)
    assert apuntar(c, None) == ARRIBA


def test_avisa_al_cambiar_de_lado():
    c = Cruce("bitcoin", 110.0, 100.0, 110.0)

    assert toca(c, ABAJO)
    assert not toca(c, ARRIBA)


def test_en_tierra_de_nadie_se_queda_como_estaba():
    c = Cruce("bitcoin", 100.2, 100.0, 100.0)

    assert not toca(c, ABAJO)
    assert apuntar(c, ABAJO) == ABAJO


def test_formatear_dorada():
    texto = formatear_cruce(Cruce("bitcoin", 66000.0, 61000.0, 68000.0), "eur")

    assert texto.startswith("🌟 <b>Cruz dorada en Bitcoin</b>\n")
    assert (
        "La media de 50 días pasa por encima de la de 200: €66.000,00 contra €61.000,00"
    ) in texto
    assert "Ahora €68.000,00" in texto
    assert "falla a menudo" in texto


def test_formatear_de_la_muerte():
    texto = formatear_cruce(Cruce("bitcoin", 58000.0, 61000.0, 55000.0), "eur")

    assert texto.startswith("☠️ <b>Cruz de la muerte en Bitcoin</b>\n")
    assert "pasa por debajo de la de 200" in texto
