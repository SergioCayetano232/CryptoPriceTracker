"""Tests de /chiste."""

import random

from crypto_tracker.alerts import formatear_chiste
from crypto_tracker.chiste import CHISTES, elegir
from crypto_tracker.comandos import interpretar


def test_salen_todos():
    salen = {elegir(random.Random(i)) for i in range(300)}

    assert salen == set(CHISTES)


def test_no_se_repiten():
    assert len(set(CHISTES)) == len(CHISTES)


def test_formatear():
    assert formatear_chiste("A & B") == "😂 A &amp; B"


def test_comando():
    assert interpretar("/chiste") == ("chiste", "")
    assert interpretar("/broma") == ("chiste", "")
