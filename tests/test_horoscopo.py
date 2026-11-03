"""Tests de /horoscopo."""

from datetime import date

import pytest

from crypto_tracker.alerts import formatear_horoscopo
from crypto_tracker.comandos import interpretar as comando
from crypto_tracker.horoscopo import (
    PREDICCIONES,
    SIGNOS,
    Horoscopo,
    HoroscopoError,
    interpretar,
    leer,
)

HOY = date(2026, 11, 3)


@pytest.mark.parametrize(
    "texto, signo",
    [
        ("aries", "aries"),
        (" Leo ", "leo"),
        ("Géminis", "geminis"),
        ("cáncer", "cancer"),
        ("escorpión", "escorpio"),
    ],
)
def test_interpretar(texto, signo):
    assert interpretar(texto) == signo


@pytest.mark.parametrize("texto", ["", "ofiuco", "bitcoin"])
def test_interpretar_mal(texto):
    with pytest.raises(HoroscopoError):
        interpretar(texto)


def test_el_mismo_dia_dice_lo_mismo():
    assert leer("aries", HOY) == leer("aries", HOY)


def test_cambia_con_los_dias():
    dias = {leer("aries", date(2026, 11, d)).prediccion for d in range(1, 29)}

    assert len(dias) > 1


def test_salen_todas_las_predicciones():
    salen = {leer(s, date(2026, 1, d)).prediccion for s in SIGNOS for d in range(1, 29)}

    assert salen == set(PREDICCIONES)


def test_numero_de_la_suerte():
    assert 1 <= leer("tauro", HOY).numero <= 99


def test_formatear():
    h = Horoscopo("♈ Aries", "Hoy no mires & no toques.", "Solana", 7)

    texto = formatear_horoscopo(h)

    assert texto == (
        "🔮 <b>♈ Aries</b>\n"
        "<i>«Hoy no mires &amp; no toques.»</i>\n\n"
        "Cripto de la suerte: <b>Solana</b>\n"
        "Número de la suerte: <b>7</b>\n"
        "<i>Es de broma: los astros no saben de criptos</i>"
    )


def test_comando():
    assert comando("/horoscopo aries") == ("horoscopo", "aries")
    assert comando("/horóscopo leo") == ("horoscopo", "leo")
