"""Tests de /dado."""

import random

from crypto_tracker.alerts import formatear_dado
from crypto_tracker.dado import tirar


def test_salen_todas():
    salen = {tirar(random.Random(i)) for i in range(100)}

    assert salen == {1, 2, 3, 4, 5, 6}


def test_formatear():
    texto = formatear_dado(6, None)

    assert texto.startswith("🎲 Ha salido un <b>6</b> ⚅: compra más")
    assert "No es un consejo" in texto


def test_formatear_con_cripto():
    assert "<b>1</b> ⚀: vende todo tu <b>Bitcoin</b>" in formatear_dado(1, "bitcoin")
    assert "no toques nada de <b>Solana</b>" in formatear_dado(3, "solana")
    assert "compra un poco de <b>Solana</b>" in formatear_dado(5, "solana")
    assert "compra más <b>Solana</b>" in formatear_dado(6, "solana")
