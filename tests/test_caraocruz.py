"""Tests de /caraocruz."""

import random

from crypto_tracker.alerts import formatear_caraocruz
from crypto_tracker.caraocruz import interpretar, lanzar


def test_salen_las_dos():
    salen = {lanzar(random.Random(i)) for i in range(50)}

    assert salen == {"cara", "cruz"}


def test_interpretar():
    assert interpretar("btc") == "bitcoin"
    assert interpretar("") is None
    assert interpretar("btc eth") is None


def test_formatear():
    texto = formatear_caraocruz("cara", None)

    assert texto.startswith("🪙 Ha salido <b>cara</b>: compra")
    assert "No es un consejo" in texto


def test_formatear_con_cripto():
    assert "<b>cruz</b>: vende <b>Bitcoin</b>" in formatear_caraocruz("cruz", "bitcoin")
