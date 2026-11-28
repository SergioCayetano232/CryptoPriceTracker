"""Tests del mensaje fijado de /envivo."""

from datetime import datetime

import pytest

from crypto_tracker.avisos import envivo


def test_a_secas_lo_pone():
    assert envivo.interpretar("") is True
    assert envivo.interpretar("  ") is True


@pytest.mark.parametrize("texto", ["no", "NO", "off", "quitar", " parar "])
def test_con_no_lo_quita(texto):
    assert envivo.interpretar(texto) is False


def test_otra_cosa_no_se_entiende():
    with pytest.raises(envivo.EnvivoError, match="/envivo no"):
        envivo.interpretar("bitcoin")


@pytest.mark.parametrize(
    "error",
    [
        "HTTP 400: Bad Request: message to edit not found",
        "HTTP 400: Bad Request: message can't be edited",
        "HTTP 400: Bad Request: MESSAGE_ID_INVALID",
        "HTTP 403: Forbidden: bot was blocked by the user",
    ],
)
def test_si_lo_borraste_se_da_por_perdido(error):
    assert envivo.se_perdio(error)


@pytest.mark.parametrize(
    "error", ["", "HTTP 502: Bad Gateway", "HTTP 429: Too Many Requests"]
)
def test_un_fallo_pasajero_no_lo_pierde(error):
    assert not envivo.se_perdio(error)


def test_el_pie_lleva_la_hora():
    assert "a las 09:05" in envivo.pie(datetime(2026, 11, 22, 9, 5))
