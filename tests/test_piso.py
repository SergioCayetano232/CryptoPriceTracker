"""Tests de /piso."""

import pytest

from crypto_tracker.alerts import formatear_piso
from crypto_tracker.piso import Piso


def test_cuantos():
    p = Piso(11_000)

    assert p.metros == pytest.approx(2)
    assert p.pisos == 0
    assert p.falta == 374_000


def test_piso_entero():
    p = Piso(800_000)

    assert p.pisos == 2
    assert p.falta == 0


def test_formatear():
    texto = formatear_piso(Piso(11_000), "eur")

    assert "🏠 <b>Tu cartera en metros de piso</b>" in texto
    assert "Vale €11.000,00" in texto
    assert "Te da para <b>2 m²</b> en Madrid" in texto
    assert "Para un piso de 70 m² te faltan €374.000,00" in texto
    assert "<i>A unos €5.500 el m², en Madrid capital</i>" in texto


def test_formatear_decimales():
    assert "<b>0,6 m²</b>" in formatear_piso(Piso(3_029), "eur")


def test_formatear_baldosa():
    texto = formatear_piso(Piso(100), "eur")

    assert "No llega ni a una baldosa 😅" in texto
    assert "te faltan" in texto


def test_formatear_pisos():
    texto = formatear_piso(Piso(800_000), "eur")
    assert "Te da para <b>145,5 m²</b>" in texto
    assert "Son <b>2 pisos</b> de 70 m²" in texto
    assert "te faltan" not in texto

    assert "Son <b>1 piso</b> de 70 m²" in formatear_piso(Piso(400_000), "eur")
