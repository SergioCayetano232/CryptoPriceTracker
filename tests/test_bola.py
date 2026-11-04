"""Tests de /bola."""

import random

import pytest

from crypto_tracker.alerts import formatear_bola
from crypto_tracker.bola import RESPUESTAS, BolaError, agitar, interpretar
from crypto_tracker.comandos import interpretar as interpretar_comando


def test_salen_todas():
    salen = {agitar(random.Random(i)) for i in range(300)}

    assert salen == set(RESPUESTAS)


def test_no_se_repiten():
    assert len(set(RESPUESTAS)) == len(RESPUESTAS)


def test_interpretar():
    assert interpretar("  ¿vendo ya?  ") == "¿vendo ya?"


def test_sin_pregunta():
    with pytest.raises(BolaError):
        interpretar("   ")


def test_formatear():
    texto = formatear_bola("¿compro <btc>?", "Mejor no.")

    assert texto == (
        "🎱 <b>¿compro &lt;btc&gt;?</b>\n"
        "<i>«Mejor no.»</i>\n"
        "<i>Es de broma: no le hagas caso a una bola</i>"
    )


def test_comando():
    assert interpretar_comando("/bola ¿vendo?") == ("bola", "¿vendo?")
    assert interpretar_comando("/bola8") == ("bola", "")
