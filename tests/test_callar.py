"""Tests de /mute con una sola cripto."""

from datetime import datetime

import pytest

from crypto_tracker.callar import interpretar
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
