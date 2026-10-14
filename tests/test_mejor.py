"""Tests de /extremo."""

from datetime import date, timedelta

import pytest

from crypto_tracker.alerts import formatear_extremo
from crypto_tracker.mejor import Dia, Extremo, calcular, interpretar
from crypto_tracker.periodo import PeriodoError

HOY = date(2026, 10, 14)


def _dias(*precios):
    """Un precio por día, el último es hoy."""
    return [
        (HOY - timedelta(days=len(precios) - 1 - i), p) for i, p in enumerate(precios)
    ]


def test_mejor_y_peor():
    e = calcular(_dias(100, 110, 99, 100))

    assert e.mejor.dia == HOY - timedelta(days=2)
    assert e.mejor.cambio == pytest.approx(10)
    assert e.peor.dia == HOY - timedelta(days=1)
    assert (e.peor.antes, e.peor.precio) == (110, 99)
    assert e.peor.cambio == pytest.approx(-10)
    assert e.dias == 3


def test_salta_los_huecos():
    dias = [(HOY - timedelta(days=10), 50.0), *_dias(100, 95)]

    e = calcular(dias)

    assert e.dias == 1  # el salto de 50 a 100 no es un día
    assert e.mejor == e.peor


def test_sin_dos_dias_seguidos():
    assert calcular([]) is None
    assert calcular(_dias(100)) is None
    assert calcular([(HOY - timedelta(days=3), 100.0), (HOY, 110.0)]) is None


def test_interpretar():
    assert interpretar("btc 7d") == ("bitcoin", 7 * 24)
    assert interpretar("solana") == ("solana", 30 * 24)
    assert interpretar("") == ("", 30 * 24)
    with pytest.raises(PeriodoError):
        interpretar("btc eth")


def test_formatear():
    e = Extremo(Dia(date(2026, 10, 3), 100, 108), Dia(date(2026, 10, 9), 110, 99), 30)

    texto = formatear_extremo("bitcoin", e, 30 * 24, "eur")

    assert "🎢 <b>Bitcoin</b>, últimos 30 días" in texto
    assert "🔺 Mejor día: <b>+8.00%</b> el 03/10" in texto
    assert "€100,00 → €108,00" in texto
    assert "🔻 Peor día: <b>-10.00%</b> el 09/10" in texto
    assert "Solo tengo" not in texto


def test_formatear_si_solo_baja_y_falta_principio():
    baja = Dia(HOY, 100, 95)

    texto = formatear_extremo("solana", Extremo(baja, baja, 1), 7 * 24, "eur", HOY)

    assert "No ha subido ningún día" in texto
    assert "Mejor día" not in texto
    assert "Peor día: <b>-5.00%</b>" in texto
    assert "Solo tengo precios desde el 14/10." in texto
