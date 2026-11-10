"""Tests de /ballena."""

import pytest

from crypto_tracker.alerts import formatear_ballena
from crypto_tracker.ballena import Ballena


@pytest.mark.parametrize(
    "btc,animal",
    [
        (0.016, "gamba"),
        (1, "cangrejo"),
        (9.99, "cangrejo"),
        (10, "pulpo"),
        (75, "pez"),
        (250, "delfín"),
        (999, "tiburón"),
        (1000, "ballena"),
        (6000, "ballena jorobada"),
    ],
)
def test_animal(btc, animal):
    assert Ballena(btc).animal[1] == animal


def test_lo_que_falta():
    b = Ballena(0.25)

    assert b.siguiente == ("🦀", "cangrejo")
    assert b.falta == pytest.approx(0.75)


def test_la_mas_grande_no_tiene_siguiente():
    b = Ballena(5000)

    assert b.siguiente is None
    assert b.falta is None


def test_formatear():
    texto = formatear_ballena(Ballena(12.5))

    assert "🐙 <b>Eres un pulpo</b>" in texto
    assert "Tienes 12,5 BTC" in texto
    assert "Para ser 🐟 pez te faltan 37,5 BTC" in texto


def test_formatear_en_femenino():
    assert "<b>Eres una gamba</b>" in formatear_ballena(Ballena(0.5))
    assert "<b>Eres una ballena</b>" in formatear_ballena(Ballena(1500))


def test_formatear_poco_en_sats():
    assert "Tienes 5.000 sats" in formatear_ballena(Ballena(0.00005))


def test_formatear_la_mas_grande():
    texto = formatear_ballena(Ballena(10_000))

    assert "🐋 <b>Eres una ballena jorobada</b>" in texto
    assert "No hay nada más grande en el mar" in texto


def test_formatear_sin_bitcoin():
    assert "no tienes bitcoin" in formatear_ballena(Ballena(0))
