"""Tests de /emoji."""

import pytest

from crypto_tracker.alerts import formatear_emoji
from crypto_tracker.comandos import interpretar
from crypto_tracker.emoji import cambio, cara


def test_cambio_de_una():
    assert cambio([(110.0, 10.0)]) == pytest.approx(10)


def test_cambio_de_varias_pesa_cada_una_por_lo_que_valia():
    # Ayer: 100 + 100. Hoy: 120 + 90.
    assert cambio([(120.0, 20.0), (90.0, -10.0)]) == pytest.approx(5)


def test_cambio_sin_nada():
    assert cambio([]) is None


@pytest.mark.parametrize(
    "porcentaje, esperada",
    [
        (-25, "💀"),
        (-10, "😱"),
        (-6, "😱"),
        (-3, "😬"),
        (-1, "😕"),
        (0, "😐"),
        (0.49, "😐"),
        (1, "🙂"),
        (3, "😎"),
        (7, "🤑"),
        (10, "🚀"),
        (40, "🚀"),
    ],
)
def test_cara(porcentaje, esperada):
    assert cara(porcentaje)[0] == esperada


def test_formatear():
    texto = formatear_emoji(3.2)

    assert texto == "😎\n\n<b>Buen día</b>\nTu cartera va <b>+3.20%</b> en 24 h"


def test_comando():
    assert interpretar("/emoji") == ("emoji", "")
    assert interpretar("/cara") == ("emoji", "")
    assert interpretar("/ánimo") == ("emoji", "")
