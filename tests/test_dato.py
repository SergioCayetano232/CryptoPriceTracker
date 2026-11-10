"""Tests de /dato."""

import random

from crypto_tracker.alerts import formatear_dato
from crypto_tracker.comandos import interpretar
from crypto_tracker.dato import DATOS, elegir


def test_salen_todos():
    salen = {elegir(random.Random(i)) for i in range(300)}

    assert salen == set(DATOS)


def test_no_se_repiten():
    assert len(set(DATOS)) == len(DATOS)


def test_formatear():
    assert formatear_dato("A & B") == "🤓 <b>¿Sabías que…?</b>\nA &amp; B"


def test_comando():
    assert interpretar("/dato") == ("dato", "")
    assert interpretar("/curiosidad") == ("dato", "")
