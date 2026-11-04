"""Tests de /tarot."""

import random

from crypto_tracker.alerts import formatear_tarot
from crypto_tracker.comandos import interpretar
from crypto_tracker.tarot import CARTAS, Carta, sacar


def test_salen_todas():
    salen = {sacar(random.Random(i)) for i in range(300)}

    assert salen == set(CARTAS)


def test_no_se_repiten():
    assert len({c.nombre for c in CARTAS}) == len(CARTAS)


def test_formatear():
    texto = formatear_tarot(Carta("La Ballena", "🐋", "Compra & vende"))

    assert texto == (
        "🃏 <b>Tu carta del tarot cripto</b>\n\n"
        "🐋 <b>La Ballena</b>\n"
        "<i>«Compra &amp; vende»</i>\n"
        "<i>Es de broma: las cartas no saben de criptos</i>"
    )


def test_comando():
    assert interpretar("/tarot") == ("tarot", "")
    assert interpretar("/carta") == ("tarot", "")
