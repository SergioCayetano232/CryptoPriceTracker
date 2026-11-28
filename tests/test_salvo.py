"""Tests de /mute ... salvo 10%."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.nucleo.config import ConfigError
from crypto_tracker.salvo import interpretar, texto, toca

AHORA = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("7d salvo 10%", ("7d", 10)),
        ("7d SALVO 12,5", ("7d", 12.5)),
        ("hasta 8:00 salvo 5%", ("hasta 8:00", 5)),
        ("2h", ("2h", None)),
        ("btc 2h", ("btc 2h", None)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


@pytest.mark.parametrize("argumento", ["7d salvo mucho", "7d salvo 0%", "salvo 10%"])
def test_interpretar_mal(argumento):
    with pytest.raises(ConfigError):
        interpretar(argumento)


def test_toca_si_pasa_del_umbral_en_cualquier_sentido():
    assert toca(12, 10, None, AHORA)
    assert toca(-10, 10, None, AHORA)
    assert not toca(9.9, 10, None, AHORA)
    assert not toca(None, 10, None, AHORA)


def test_una_vez_al_dia():
    assert not toca(15, 10, AHORA - timedelta(hours=23), AHORA)
    assert toca(15, 10, AHORA - timedelta(hours=24), AHORA)


def test_texto():
    t = texto("bitcoin", 55000, -12.34, "eur", AHORA + timedelta(days=3))

    assert t.startswith("🚨 <b>Bitcoin</b> 🔻 -12,3% en 24 h, ahora €55.000,00")
    assert "callado hasta el" in t
    assert "/unmute" in t
