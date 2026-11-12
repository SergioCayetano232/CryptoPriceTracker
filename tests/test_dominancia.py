"""Tests de /dominancia."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.alerts import formatear_dominancia
from crypto_tracker.dominancia import Dominancia, Foto, calcular, hace, toca_guardar
from crypto_tracker.mercado import Mercado

AHORA = datetime(2026, 11, 12, 12, tzinfo=timezone.utc)


def _hace(dias, horas=0):
    return AHORA - timedelta(days=dias, hours=horas)


def _foto(dias, bitcoin, horas=0):
    return Foto(_hace(dias, horas), bitcoin, 12.0, 6.0)


def _mercado(bitcoin=58.0):
    return Mercado(2.4e12, 1.2, bitcoin, 12.5, 6.5)


def test_toca_guardar_una_al_dia():
    assert toca_guardar(None, AHORA)
    assert not toca_guardar(AHORA - timedelta(hours=1), AHORA)
    assert toca_guardar(AHORA - timedelta(days=1), AHORA)


def test_hace_la_mas_cercana():
    fotos = [_foto(8, 55.0), _foto(7, 56.0, horas=3), _foto(6, 57.0)]
    assert hace(fotos, AHORA, 7).bitcoin == 56.0


def test_hace_muy_lejos():
    assert hace([_foto(3, 55.0)], AHORA, 7) is None
    assert hace([], AHORA, 1) is None


def test_ayer_aunque_sea_de_hace_30_horas():
    assert hace([_foto(1, 57.0, horas=6)], AHORA, 1).bitcoin == 57.0


def test_calcular():
    fotos = [_foto(30, 54.0), _foto(7, 56.5), _foto(1, 57.5)]
    d = calcular(_mercado(58.0), fotos, AHORA)

    assert d.cambios == [(1, pytest.approx(0.5)), (7, 1.5), (30, 4.0)]
    assert d.hacia == "bitcoin"


def test_hacia_mira_lo_mas_largo():
    # En la semana ha ganado, pero en el mes ha perdido: manda el mes.
    fotos = [_foto(30, 61.0), _foto(7, 56.0)]
    assert calcular(_mercado(58.0), fotos, AHORA).hacia == "altcoins"


def test_hacia_quieta_o_sin_datos():
    assert calcular(_mercado(58.0), [_foto(7, 57.5)], AHORA).hacia == ""
    assert calcular(_mercado(58.0), [_foto(1, 50.0)], AHORA).hacia is None


def test_formatear():
    d = Dominancia(_mercado(58.0), [(1, 0.5), (7, 1.5), (30, -4.0)])
    texto = formatear_dominancia(d)

    assert "👑 <b>Dominancia de Bitcoin: 58,0%</b>" in texto
    assert "🔺 +0,5 puntos en 24 h" in texto
    assert "🔻 -4,0 puntos en 30 días" in texto
    assert "Ethereum: 12,5%" in texto
    assert "Estables: 6,5%" in texto
    assert "El resto de altcoins: 23,0%" in texto


def test_formatear_hacia():
    hacia_btc = Dominancia(_mercado(), [(7, 1.5)])
    hacia_alts = Dominancia(_mercado(), [(7, -1.5)])
    quieta = Dominancia(_mercado(), [(7, 0.2)])

    assert "El dinero vuelve a bitcoin" in formatear_dominancia(hacia_btc)
    assert "El dinero se va a las altcoins" in formatear_dominancia(hacia_alts)
    assert "Ni a un lado ni a otro" in formatear_dominancia(quieta)


def test_formatear_sin_fotos():
    texto = formatear_dominancia(Dominancia(_mercado(), []))
    assert "Aún no tengo de días anteriores" in texto
