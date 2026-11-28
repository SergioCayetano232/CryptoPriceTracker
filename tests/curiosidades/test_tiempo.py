"""Tests de /tiempo."""

import pytest

from crypto_tracker.avisos.alerts import formatear_tiempo
from crypto_tracker.curiosidades.emoji import CARAS
from crypto_tracker.curiosidades.tiempo import PARTE, parte
from crypto_tracker.nucleo.comandos import interpretar


@pytest.mark.parametrize(
    "porcentaje, cielo",
    [
        (-25, "Huracán"),
        (-10, "Tormenta"),
        (-3, "Lluvia"),
        (-1, "Chubascos"),
        (0, "Nublado"),
        (0.5, "Claros"),
        (3, "Soleado"),
        (7, "Ola de calor"),
        (10, "Erupción"),
        (80, "Erupción"),
    ],
)
def test_parte(porcentaje, cielo):
    assert parte(porcentaje)[1] == cielo


def test_mismos_cortes_que_emoji():
    assert [p[0] for p in PARTE] == [c[0] for c in CARAS]


def test_formatear():
    texto = formatear_tiempo(-6.2)

    assert texto.startswith("⛈️ <b>Tormenta</b>")
    assert "Tu cartera va <b>-6.20%</b> en 24 h" in texto
    assert "<i>Mejor no abrir el exchange hasta que escampe</i>" in texto


def test_alias():
    assert interpretar("/clima")[0] == "tiempo"
