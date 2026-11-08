"""Tests del aviso de RSI."""

import pytest

from crypto_tracker.avisorsi import ALTA, BAJA, sigue, toca, zona


@pytest.mark.parametrize(
    "valor, sale",
    [
        (70, ALTA),
        (85, ALTA),
        (69.9, None),
        (50, None),
        (30.1, None),
        (30, BAJA),
        (5, BAJA),
    ],
)
def test_zona(valor, sale):
    assert zona(valor) == sale


@pytest.mark.parametrize(
    "valor, avisado, sale",
    [
        (75, None, ALTA),
        (25, None, BAJA),
        (50, None, None),
        (75, ALTA, None),  # ya avisada
        (25, BAJA, None),
        (25, ALTA, BAJA),  # de golpe a la otra punta
        (75, BAJA, ALTA),
        (66, ALTA, None),
    ],
)
def test_toca(valor, avisado, sale):
    assert toca(valor, avisado) == sale


@pytest.mark.parametrize(
    "valor, avisado, sale",
    [
        (66, ALTA, ALTA),  # rondando el límite, no se olvida
        (65, ALTA, ALTA),
        (64.9, ALTA, None),  # ya se ha alejado
        (34, BAJA, BAJA),
        (35, BAJA, BAJA),
        (35.1, BAJA, None),
        (50, None, None),
    ],
)
def test_sigue(valor, avisado, sale):
    assert sigue(valor, avisado) == sale
