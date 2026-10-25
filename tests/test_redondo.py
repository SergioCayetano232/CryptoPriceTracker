"""Tests de /redondo."""

import pytest

from crypto_tracker.alerts import formatear_redondo
from crypto_tracker.redondo import calcular, escalon


@pytest.mark.parametrize(
    "precio,esperado",
    [
        (63200, 10000),
        (98500, 10000),
        (10500, 1000),
        (19900, 1000),
        (2500, 1000),
        (0.35, 0.1),
        (0.15, 0.01),
        (0.00002345, 0.00001),
    ],
)
def test_escalon(precio, esperado):
    assert escalon(precio) == pytest.approx(esperado)


@pytest.mark.parametrize(
    "precio,arriba,abajo",
    [
        (63200, 70000, 60000),
        (98500, 100000, 90000),
        (10500, 11000, 10000),
        (0.35, 0.4, 0.3),
        # Justo en una redonda: las de al lado, no ella misma.
        (60000, 70000, 50000),
        (0.3, 0.4, 0.2),
    ],
)
def test_calcular(precio, arriba, abajo):
    r = calcular(precio)
    assert r.arriba == arriba
    assert r.abajo == abajo


def test_lo_que_falta():
    r = calcular(64000)
    assert r.falta_arriba == pytest.approx(9.375)
    assert r.falta_abajo == pytest.approx(-6.25)


def test_formatear():
    texto = formatear_redondo(
        [("bitcoin", calcular(64000)), ("ripple", calcular(0.5))], "eur"
    )

    assert "🎯 <b>Bitcoin</b>  ahora €64.000,00" in texto
    assert "⬆️ €70.000,00  a <b>+9.38%</b>" in texto
    assert "⬇️ €60.000,00  a <b>-6.25%</b>" in texto
    assert "⬆️ €0,6000  a <b>+20.00%</b>" in texto
    assert texto.count("🎯") == 2
