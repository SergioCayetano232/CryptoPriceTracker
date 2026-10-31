"""Tests de /consejo."""

import random

from crypto_tracker.alerts import formatear_consejo
from crypto_tracker.consejo import CONSEJOS, elegir


def test_salen_todos():
    salen = {elegir(random.Random(i)) for i in range(300)}

    assert salen == set(CONSEJOS)


def test_no_se_repiten():
    assert len(set(CONSEJOS)) == len(CONSEJOS)


def test_formatear():
    texto = formatear_consejo("Compra & vende")

    assert texto == (
        "🧠 <b>Consejo de inversión</b>\n"
        "<i>«Compra &amp; vende»</i>\n"
        "<i>Es de broma, no le hagas caso</i>"
    )
