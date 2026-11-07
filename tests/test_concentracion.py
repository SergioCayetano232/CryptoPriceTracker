"""Tests del aviso de concentración."""

import pytest

from crypto_tracker.cartera import Valor
from crypto_tracker.concentracion import Concentracion, mayor, sigue, toca

LIMITE = 70


def _valores(**cuanto):
    return [Valor(c, v) for c, v in cuanto.items()]


def test_mayor():
    c = mayor(_valores(bitcoin=7500, solana=2000, ethereum=500))

    assert c.coin_id == "bitcoin"
    assert c.peso == pytest.approx(75)
    assert c.si_cae == pytest.approx(15)


def test_con_una_sola_no_hay_nada_que_avisar():
    assert mayor(_valores(bitcoin=1000)) is None
    assert mayor(_valores(bitcoin=1000, shiba=0)) is None


@pytest.mark.parametrize(
    "peso, avisado, sale",
    [
        (75, None, True),
        (70, None, True),
        (69, None, False),
        (75, "bitcoin", False),  # ya avisado
        (75, "solana", True),  # ahora es otra
    ],
)
def test_toca(peso, avisado, sale):
    assert toca(Concentracion("bitcoin", peso), LIMITE, avisado) == sale


def test_sin_cartera_no_toca():
    assert not toca(None, LIMITE, None)


@pytest.mark.parametrize(
    "peso, sale",
    [
        (75, "bitcoin"),
        (68, "bitcoin"),  # rondando el límite no se vuelve a avisar
        (65, "bitcoin"),
        (64.9, None),  # bajó de verdad: la próxima vez avisa
    ],
)
def test_sigue(peso, sale):
    assert sigue(Concentracion("bitcoin", peso), LIMITE, "bitcoin") == sale


def test_sigue_si_ahora_manda_otra_se_olvida():
    assert sigue(Concentracion("solana", 60), LIMITE, "bitcoin") is None


def test_sigue_sin_cartera_se_olvida():
    assert sigue(None, LIMITE, "bitcoin") is None


def test_el_ciclo_entero():
    """Sube, avisa una vez, ronda el límite sin repetir, baja y vuelve a avisar."""
    avisado, avisos = None, 0
    for peso in [60, 72, 74, 69, 71, 63, 71]:
        c = Concentracion("bitcoin", peso)
        if toca(c, LIMITE, avisado):
            avisos += 1
            avisado = c.coin_id
        else:
            avisado = sigue(c, LIMITE, avisado)

    assert avisos == 2
