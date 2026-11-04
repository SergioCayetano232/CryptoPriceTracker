"""Tests de /refran."""

import random

from crypto_tracker.alerts import formatear_refran
from crypto_tracker.comandos import interpretar
from crypto_tracker.refran import REFRANES, elegir


def test_salen_todos():
    salen = {elegir(random.Random(i)) for i in range(300)}

    assert salen == set(REFRANES)


def test_no_se_repiten():
    assert len(set(REFRANES)) == len(REFRANES)


def test_formatear():
    texto = formatear_refran("Satoshi & cía")

    assert texto == (
        "📜 <b>Refranero cripto</b>\n"
        "<i>«Satoshi &amp; cía»</i>\n"
        "<i>Como decía mi abuela, que no tenía ni un bitcoin</i>"
    )


def test_comando():
    assert interpretar("/refran") == ("refran", "")
    assert interpretar("/refrán") == ("refran", "")
    assert interpretar("/dicho") == ("refran", "")
