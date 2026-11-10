"""Tests de /apodo."""

import pytest

from crypto_tracker.alerts import formatear_apodo
from crypto_tracker.apodo import Perfil, elegir
from crypto_tracker.comandos import interpretar

DOS = ["bitcoin", "ethereum"]


@pytest.mark.parametrize(
    "perfil, mote",
    [
        (Perfil([], 0, 0, None, None), "El Mirón"),
        (Perfil(DOS, 3, 0, 10, -60.0), "Comprador de picos"),
        (Perfil(DOS, 3, 0, 10, 150.0), "El Visionario"),
        (Perfil(DOS, 2, 5, 10, 20.0), "Manos de papel"),
        (Perfil(["bitcoin"], 2, 0, 10, 20.0), "Maximalista"),
        (Perfil(list("abcdef"), 2, 0, 10, 20.0), "El Coleccionista"),
        (Perfil(DOS, 2, 0, 400, 20.0), "Manos de diamante"),
        (Perfil(DOS, 12, 1, 400, 20.0), "Comprador compulsivo"),
        (Perfil(DOS, 2, 1, 30, None), "Hodler tranquilo"),
    ],
)
def test_elegir(perfil, mote):
    assert elegir(perfil)[1] == mote


def test_lo_gordo_gana_a_lo_demas():
    # Solo bitcoin pero a -70%: pesa más lo de los picos.
    assert elegir(Perfil(["bitcoin"], 1, 0, 10, -70.0))[1] == "Comprador de picos"


def test_diamante_no_si_has_vendido():
    assert elegir(Perfil(DOS, 2, 1, 400, 20.0))[1] == "Hodler tranquilo"


def test_formatear():
    texto = formatear_apodo(("🧻", "Manos de papel", "Has vendido 5 veces"))

    assert texto == "🧻 Te llamaremos <b>Manos de papel</b>\n<i>Has vendido 5 veces</i>"


def test_comando():
    assert interpretar("/apodo") == ("apodo", "")
    assert interpretar("/mote") == ("apodo", "")
