"""Tests de /bigmac."""

from crypto_tracker.alerts import formatear_bigmac
from crypto_tracker.bigmac import BigMac


def test_cuantos():
    assert BigMac(2_000).cuantos == 363
    assert BigMac(5).cuantos == 0


def test_formatear():
    texto = formatear_bigmac(BigMac(2_000), "eur")

    assert "🍔 <b>Tu cartera en Big Macs</b>" in texto
    assert "Vale €2.000,00" in texto
    assert "Te da para <b>363 Big Macs</b>" in texto
    assert "<i>A unos €5,50 cada uno</i>" in texto


def test_formatear_uno_y_ninguno():
    assert "<b>1 Big Mac</b>" in formatear_bigmac(BigMac(6), "eur")
    assert "No te da ni para un Big Mac" in formatear_bigmac(BigMac(5), "eur")
