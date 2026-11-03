"""Tests de /excusa."""

import random

from crypto_tracker.alerts import formatear_excusa
from crypto_tracker.comandos import interpretar
from crypto_tracker.excusa import EXCUSAS, elegir


def test_salen_todas():
    salen = {elegir(random.Random(i)) for i in range(300)}

    assert salen == set(EXCUSAS)


def test_no_se_repiten():
    assert len(set(EXCUSAS)) == len(EXCUSAS)


def test_formatear():
    texto = formatear_excusa("La Fed & los ETF")

    assert texto == (
        "🤷 <b>Excusa para hoy</b>\n"
        "<i>«La Fed &amp; los ETF»</i>\n"
        "<i>Cópiala y pégala en el grupo, que nadie pregunte más</i>"
    )


def test_comando():
    assert interpretar("/excusa") == ("excusa", "")
    assert interpretar("/excusas") == ("excusa", "")
