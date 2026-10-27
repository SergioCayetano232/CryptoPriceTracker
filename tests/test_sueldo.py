"""Tests de /sueldo."""

import pytest

from crypto_tracker.alerts import formatear_sueldo
from crypto_tracker.sueldo import MENSUAL, Sueldo


def test_meses():
    assert pytest.approx(1424.5) == MENSUAL
    assert Sueldo(14_245).meses == pytest.approx(10)


def test_formatear_meses():
    texto = formatear_sueldo(Sueldo(12_000))

    assert "💼 <b>Tu cartera en sueldos</b>" in texto
    assert "Vale €12.000,00" in texto
    assert "Son <b>8,4 meses</b> de salario mínimo" in texto
    assert "<i>El SMI de 2026: €1.221 en 14 pagas</i>" in texto


def test_formatear_años():
    assert "Son <b>2,0 años</b>" in formatear_sueldo(Sueldo(34_188))


def test_formatear_uno():
    assert "Son <b>1,0 mes</b>" in formatear_sueldo(Sueldo(1_424.5))
    assert "Son <b>1,0 año</b>" in formatear_sueldo(Sueldo(17_094))


def test_no_llega_a_un_mes():
    texto = formatear_sueldo(Sueldo(500))

    assert "No llega ni a un mes de salario mínimo" in texto
    assert "Son" not in texto
