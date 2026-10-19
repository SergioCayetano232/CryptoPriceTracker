"""Tests de /hoy."""

from datetime import datetime, timedelta

import pytest

from crypto_tracker.alerts import formatear_hoy
from crypto_tracker.hoy import Hoy, calcular, medianoche, mejor_y_peor

CERO = datetime(2026, 10, 15).astimezone()  # las 00:00 de aquí


def _a(minutos, precio):
    return (CERO + timedelta(minutes=minutos), precio)


def test_desde_el_ultimo_de_ayer():
    serie = [_a(-30, 90.0), _a(-5, 100.0), _a(60, 120.0), _a(120, 95.0), _a(180, 110.0)]

    h = calcular(serie, CERO)

    assert h.antes == 100.0
    assert h.ahora == 110.0
    assert h.cambio == pytest.approx(10)
    assert (h.maximo, h.minimo) == (120.0, 95.0)
    assert h.desde is None


def test_sin_el_de_ayer_cuenta_desde_el_primero_de_hoy():
    h = calcular([_a(200, 100.0), _a(300, 105.0)], CERO)

    assert h.antes == 100.0
    assert h.cambio == pytest.approx(5)
    assert h.desde == CERO + timedelta(minutes=200)


def test_sin_nada_de_hoy():
    assert calcular([], CERO) is None
    assert calcular([_a(-10, 100.0)], CERO) is None


def test_medianoche():
    assert medianoche(CERO + timedelta(hours=15, minutes=7)) == CERO


def test_formatear():
    lineas = [
        ("bitcoin", Hoy(100.0, 110.0, 120.0, 95.0, None)),
        ("solana", Hoy(10.0, 9.0, 10.0, 9.0, CERO + timedelta(hours=3, minutes=15))),
        ("ethereum", None),
    ]

    texto = formatear_hoy(lineas, "eur", CERO + timedelta(hours=15, minutes=5))

    assert texto.startswith("☀️ <b>Hoy</b>, desde las 00:00\n\n")
    assert "<b>Bitcoin</b>  €110,00  🔺 +10.00%\n" in texto
    assert "   <i>máx €120,00 · mín €95,00</i>" in texto
    assert "<b>Solana</b>  €9,00  🔻 -10.00% <i>(desde las 03:15)</i>" in texto
    assert "<b>Ethereum</b>  <i>(sin precios de hoy)</i>" in texto
    assert texto.endswith("<i>Con lo guardado, lo último de las 15:05</i>")


def _hoy(cambio, desde=None):
    return Hoy(100.0, 100.0 + cambio, 120.0, 90.0, desde)


def test_mejor_y_peor():
    lineas = [("bitcoin", _hoy(2)), ("ethereum", _hoy(-3)), ("solana", _hoy(5))]

    assert mejor_y_peor(lineas) == ("solana", "ethereum")


def test_mejor_y_peor_con_dos_no_sale():
    assert mejor_y_peor([("bitcoin", _hoy(2)), ("ethereum", _hoy(-3))]) is None


def test_mejor_y_peor_sin_las_que_empiezan_tarde_ni_sin_precio():
    tarde = CERO + timedelta(hours=3)
    lineas = [
        ("bitcoin", _hoy(2)),
        ("ethereum", _hoy(-3)),
        ("solana", _hoy(9, tarde)),
        ("cardano", None),
    ]

    assert mejor_y_peor(lineas) is None


def test_mejor_y_peor_si_van_igual_no_sale():
    lineas = [(c, _hoy(1)) for c in ("bitcoin", "ethereum", "solana")]

    assert mejor_y_peor(lineas) is None


def test_formatear_marca_la_mejor_y_la_peor():
    lineas = [("bitcoin", _hoy(2)), ("ethereum", _hoy(-3)), ("solana", _hoy(5))]

    texto = formatear_hoy(lineas, "eur", CERO + timedelta(hours=15))

    assert "<b>Solana</b>  €105,00  🔺 +5.00%  <i>← la mejor</i>\n" in texto
    assert "<b>Ethereum</b>  €97,00  🔻 -3.00%  <i>← la peor</i>\n" in texto
    assert "<b>Bitcoin</b>  €102,00  🔺 +2.00%\n" in texto
