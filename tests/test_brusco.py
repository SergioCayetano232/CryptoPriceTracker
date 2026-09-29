"""Tests de los movimientos bruscos."""

import pytest

from crypto_tracker.alerts import ALTO, BAJO, formatear
from crypto_tracker.brusco import revisar


def test_caida_fuerte():
    aviso = revisar("bitcoin", [60000.0, 59000.0, 55000.0], 8, 60)

    assert aviso.estado == BAJO
    assert aviso.threshold == 60000.0
    assert aviso.percent == pytest.approx(-8.333, abs=0.001)


def test_subida_fuerte():
    aviso = revisar("bitcoin", [60000.0, 62000.0, 65000.0], 8, 60)

    assert aviso.estado == ALTO
    assert aviso.threshold == 60000.0


def test_se_queda_corto():
    assert revisar("bitcoin", [60000.0, 57000.0], 8, 60) is None


def test_cuenta_desde_el_maximo_no_desde_el_primero():
    # sube un 10% y lo devuelve todo: el primero y el ultimo son iguales
    aviso = revisar("bitcoin", [60000.0, 66000.0, 60000.0], 8, 60)

    assert aviso is not None
    assert aviso.estado == BAJO
    assert aviso.threshold == 66000.0


def test_justo_en_el_limite_avisa():
    assert revisar("bitcoin", [100.0, 92.0], 8, 60) is not None


@pytest.mark.parametrize("precios", [[], [60000.0]])
def test_sin_datos_no_avisa(precios):
    assert revisar("bitcoin", precios, 8, 60) is None


def test_el_mensaje():
    aviso = revisar("bitcoin", [60000.0, 55000.0], 8, 60)
    texto = formatear(aviso, "eur")

    assert "⚡" in texto
    assert "ha caído" in texto
    assert "8.33%" in texto
    assert "1 h" in texto
    assert "60.000,00" in texto
    assert "55.000,00" in texto


def test_el_mensaje_en_minutos():
    aviso = revisar("bitcoin", [100.0, 120.0], 8, 90)

    assert "90 min" in formatear(aviso, "eur")
    assert "ha subido" in formatear(aviso, "eur")
