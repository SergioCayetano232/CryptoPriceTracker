"""Tests de /mute con una sola cripto."""

from datetime import datetime

import pytest

from crypto_tracker.callar import a_secas, interpretar
from crypto_tracker.config import ConfigError

AHORA = datetime(2026, 10, 11, 22, 0).astimezone()


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("2h", (None, 120)),
        ("hasta 23:30", (None, 90)),
        ("btc 2h", ("bitcoin", 120)),
        ("Solana 30m", ("solana", 30)),
        ("eth hasta 8:00", ("ethereum", 600)),
        ("pepe 1d", ("pepe", 1440)),  # las que no son conocidas, con su id
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento, AHORA) == esperado


def test_la_cripto_sin_tiempo_pregunta_cuanto():
    with pytest.raises(ConfigError, match="/mute btc 2h"):
        interpretar("btc", AHORA)


@pytest.mark.parametrize("argumento", ["mucho", "hasta mañana", "btc mucho"])
def test_tiempo_mal_escrito_no_pregunta_por_la_cripto(argumento):
    with pytest.raises(ConfigError) as e:
        interpretar(argumento, AHORA)
    assert "¿Cuánto tiempo?" not in str(e.value)


# --- /mute a secas ---


def test_a_secas_sin_nada_callado_pregunta():
    assert a_secas(None, {}) == "🔕 ¿Cuánto tiempo me callo?"


def test_a_secas_callado_todo():
    hasta = datetime(2026, 10, 12, 8, 0).astimezone()

    assert a_secas(hasta, {}) == (
        "🔕 Ya estoy callado hasta las 08:00 del 12/10.\n¿Vuelvo a avisar o lo cambio?"
    )


def test_a_secas_dice_las_calladas_la_primera_que_vuelve_arriba():
    calladas = {
        "solana": datetime(2026, 10, 13, 9, 0).astimezone(),
        "bitcoin": datetime(2026, 10, 12, 0, 30).astimezone(),
    }

    assert a_secas(None, calladas) == (
        "🔕 Ahora no te aviso de:\n"
        "<b>Bitcoin</b> hasta las 00:30 del 12/10 · /unmute bitcoin\n"
        "<b>Solana</b> hasta las 09:00 del 13/10 · /unmute solana\n"
        "\n¿Cuánto tiempo me callo con todas?"
    )


def test_a_secas_callado_todo_y_una_aparte():
    hasta = datetime(2026, 10, 12, 8, 0).astimezone()
    calladas = {"bitcoin": datetime(2026, 10, 14, 8, 0).astimezone()}

    texto = a_secas(hasta, calladas)

    assert texto.startswith("🔕 Ya estoy callado hasta las 08:00 del 12/10.\n")
    assert (
        "Y aparte, cada una por su lado:\n<b>Bitcoin</b> hasta las 08:00 del 14/10"
        in texto
    )
    assert texto.endswith("14/10 · /unmute bitcoin\n\n¿Vuelvo a avisar o lo cambio?")
