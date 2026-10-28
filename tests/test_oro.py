"""Tests de /oro."""

import pytest

from crypto_tracker.alerts import formatear_oro
from crypto_tracker.oro import Oro


def test_cuentas():
    o = Oro(7_000, 3_110.35)

    assert o.gramo == pytest.approx(100)
    assert o.gramos == pytest.approx(70)
    assert o.onzas == pytest.approx(2.25, abs=0.01)


def test_formatear():
    texto = formatear_oro(Oro(7_000, 3_110.35), "eur")

    assert "🥇 <b>Tu cartera en oro</b>" in texto
    assert "Vale €7.000,00" in texto
    assert "Son <b>70 gramos</b>, 2,25 onzas" in texto
    assert "<i>Con el gramo a €100,00</i>" in texto


def test_formatear_mucho():
    # Con más de un kilo lo paso a kilos, que 1.500 gramos se lee peor
    texto = formatear_oro(Oro(150_000, 3_110.35), "eur")
    assert "Son <b>1,5 kilos</b>" in texto


def test_formatear_poco():
    assert "Son <b>0,5 gramos</b>" in formatear_oro(Oro(50, 3_110.35), "eur")
