"""Tests de /frase."""

import random

from crypto_tracker.alerts import formatear_frase
from crypto_tracker.frase import FRASES, Frase, elegir


def test_salen_todas():
    salen = {elegir(random.Random(i)) for i in range(300)}

    assert salen == set(FRASES)


def test_formatear():
    texto = formatear_frase(Frase("Running bitcoin", "Hal Finney", 2009))

    assert texto == "💬 <i>«Running bitcoin»</i>\n— Hal Finney, 2009"


def test_formatear_sin_año():
    texto = formatear_frase(Frase("Hola", "Alguien"))

    assert texto.endswith("— Alguien")
