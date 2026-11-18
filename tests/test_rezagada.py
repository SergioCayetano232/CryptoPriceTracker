"""Tests de /rezagada."""

import pytest

from crypto_tracker.alerts import formatear_aviso_rezagada, formatear_rezagadas
from crypto_tracker.rezagada import (
    Rezagada,
    RezagadaError,
    diferencia,
    interpretar,
    toca,
)


def test_interpretar():
    assert interpretar("eth btc 10") == ("ethereum", "bitcoin", 10)
    assert interpretar("eth btc 7,5%") == ("ethereum", "bitcoin", 7.5)
    assert interpretar("eth btc no") == ("ethereum", "bitcoin", None)


@pytest.mark.parametrize(
    "argumento, error",
    [
        ("eth 10", "Escríbelo así"),
        ("btc bitcoin 10", "la misma"),
        ("eth btc mucho", "no es un %"),
        ("eth btc 0", "no es un %"),
        ("eth btc 150", "no es un %"),
    ],
)
def test_interpretar_mal(argumento, error):
    with pytest.raises(RezagadaError, match=error):
        interpretar(argumento)


def test_diferencia():
    # eth -10%, btc +10%: 0,9 / 1,1 = 0,818 -> -18,2%
    assert diferencia(90, 100, 110, 100) == pytest.approx(-18.18, abs=0.01)
    assert diferencia(110, 100, 110, 100) == pytest.approx(0)


@pytest.mark.parametrize(
    "avisada, dif, sale",
    [
        (False, -9.0, (False, False)),
        (False, -10.0, (True, True)),
        (True, -12.0, (False, True)),  # ya avisada: no repite
        (True, -6.0, (False, True)),  # recupera algo, pero no la mitad
        (True, -4.0, (False, False)),  # recupera la mitad: lista para otra vez
    ],
)
def test_toca(avisada, dif, sale):
    assert toca(Rezagada("ethereum", "bitcoin", 10, avisada), dif) == sale


def test_formatear():
    r = Rezagada("ethereum", "bitcoin", 10)
    aviso = formatear_aviso_rezagada(r, -18.18, -10, 10)

    assert "<b>Ethereum</b> se queda atrás: en 7 días va un <b>-18.2%</b>" in aviso
    assert "Ethereum -10.0% · Bitcoin +10.0%" in aviso
    assert "Ethereum</b> contra Bitcoin: 10% peor" in formatear_rezagadas([r])
    assert "No vigilas ninguna" in formatear_rezagadas([])
