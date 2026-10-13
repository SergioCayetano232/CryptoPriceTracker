"""Tests de /cuando."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.alerts import formatear_cuando
from crypto_tracker.cuando import Cuando, CuandoError, calcular, interpretar

INICIO = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)
AHORA = INICIO + timedelta(days=40)


def _serie(*precios):
    return [(INICIO + timedelta(days=i), p) for i, p in enumerate(precios)]


def _dia(n):
    return INICIO + timedelta(days=n)


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("bitcoin 60000", ("bitcoin", 60000)),
        ("btc 60k", ("bitcoin", 60000)),
        ("btc a 60.000 €", ("bitcoin", 60000)),
        ("sol 0,35", ("solana", 0.35)),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


@pytest.mark.parametrize("argumento", ["", "bitcoin", "bitcoin mucho", "btc -5"])
def test_interpretar_mal(argumento):
    with pytest.raises(CuandoError, match="/cuando bitcoin 60000"):
        interpretar(argumento)


def test_calcular_cuando_bajo():
    c = calcular(_serie(50, 70, 58, 65, 80), 60)

    assert c.por_debajo
    assert (c.cuando, c.precio) == (_dia(2), 58)  # la última, no la primera
    assert c.cambio == pytest.approx(80 / 58 * 100 - 100)


def test_calcular_cuando_subio():
    c = calcular(_serie(100, 130, 90, 70), 120)

    assert not c.por_debajo
    assert (c.cuando, c.precio) == (_dia(1), 130)


def test_calcular_nunca_ha_llegado():
    c = calcular(_serie(70, 65, 80), 60)

    assert c.cuando is None
    assert c.cambio is None
    assert (c.extremo, c.desde) == (65, _dia(0))


def test_calcular_justo_ahora():
    c = calcular(_serie(70, 60), 60)

    assert c.cuando == _dia(1)


def test_calcular_sin_datos():
    assert calcular([], 60) is None


def test_formatear():
    c = Cuando(60, 80, True, _dia(2), 58, _dia(0), 58)

    texto = formatear_cuando("bitcoin", c, "eur", AHORA)

    assert (
        "🔎 La última vez que <b>Bitcoin</b> estuvo a <b>€60,00</b> o menos "
        "fue <b>el 03/09</b>, hace 38 días"
    ) in texto
    assert "Entonces €58,00, ahora €80,00 (+37.93%)" in texto


def test_formatear_por_encima():
    c = Cuando(120, 70, False, _dia(1), 130, _dia(0), 130)

    assert "<b>€120,00</b> o más" in formatear_cuando("bitcoin", c, "eur", AHORA)


def test_formatear_nunca():
    c = Cuando(60, 80, True, None, None, _dia(0), 65)

    texto = formatear_cuando("bitcoin", c, "eur", AHORA)

    assert "<b>Bitcoin</b> no ha bajado a €60,00 desde el 01/09" in texto
    assert "Lo más bajo, €65,00. Ahora €80,00" in texto


def test_formatear_justo_ahora():
    c = Cuando(60, 60, True, AHORA, 60, _dia(0), 60)

    assert "está justo a ese precio ahora" in formatear_cuando(
        "bitcoin", c, "eur", AHORA
    )
