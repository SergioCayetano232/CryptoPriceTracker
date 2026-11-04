"""Tests de /galleta."""

from datetime import date, timedelta

from crypto_tracker.alerts import formatear_galleta
from crypto_tracker.comandos import interpretar
from crypto_tracker.galleta import FRASES, Galleta, abrir


def test_mismo_dia_misma_galleta():
    assert abrir(date(2026, 11, 4)) == abrir(date(2026, 11, 4))


def test_cambia_con_los_dias():
    dias = [date(2026, 1, 1) + timedelta(days=i) for i in range(300)]

    assert {abrir(d).frase for d in dias} == set(FRASES)


def test_numeros():
    for i in range(50):
        numeros = abrir(date(2026, 1, 1) + timedelta(days=i)).numeros

        assert len(set(numeros)) == 6
        assert numeros == sorted(numeros)
        assert all(1 <= n <= 49 for n in numeros)


def test_no_se_repiten():
    assert len(set(FRASES)) == len(FRASES)


def test_formatear():
    texto = formatear_galleta(Galleta("Compra & vende", [3, 7, 12, 25, 33, 41]))

    assert texto == (
        "🥠 <b>Tu galleta de la suerte</b>\n"
        "<i>«Compra &amp; vende»</i>\n\n"
        "Números de la suerte: <b>3 · 7 · 12 · 25 · 33 · 41</b>\n"
        "<i>Hasta mañana no te toca otra</i>"
    )


def test_comando():
    assert interpretar("/galleta") == ("galleta", "")
    assert interpretar("/fortuna") == ("galleta", "")
