"""Tests de /sat."""

import pytest

from crypto_tracker.alerts import formatear_sat
from crypto_tracker.sat import Sat


def test_cuanto_vale_uno():
    s = Sat(70_000)

    assert s.valor == pytest.approx(0.0007)
    assert s.por(1) == 1429
    assert s.por(100) == 142857


def test_formatear():
    texto = formatear_sat(Sat(70_000), "eur")

    assert "⚡ <b>1 sat vale €0,0007</b>" in texto
    assert "€1 → 1.429 sats" in texto
    assert "€10 → 14.286 sats" in texto
    assert "€100 → 142.857 sats" in texto
    assert "<i>Un bitcoin son 100 millones de sats, a €70.000,00</i>" in texto
