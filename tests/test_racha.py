"""Tests de /racha."""

from datetime import date, timedelta

import pytest

from crypto_tracker.alerts import formatear_racha
from crypto_tracker.racha import Racha, calcular

HOY = date(2026, 10, 12)


def _dias(*precios):
    """Un precio por día, el último es hoy."""
    return [
        (HOY - timedelta(days=len(precios) - 1 - i), p) for i, p in enumerate(precios)
    ]


def test_racha_subiendo():
    r = calcular(_dias(120, 100, 101, 105, 110))

    assert r.sube
    assert r.dias == 3
    assert r.desde == HOY - timedelta(days=3)
    assert (r.antes, r.ahora) == (100, 110)
    assert r.cambio == pytest.approx(10)
    assert r.entera


def test_racha_bajando():
    r = calcular(_dias(90, 100, 95))

    assert not r.sube
    assert r.dias == 1


def test_racha_hasta_donde_hay_datos():
    r = calcular(_dias(100, 101, 102))

    assert r.dias == 2
    assert not r.entera  # puede venir de antes


def test_racha_se_corta_si_falta_un_dia():
    dias = [(HOY - timedelta(days=5), 50.0), *_dias(100, 105, 110)]

    r = calcular(dias)

    assert r.dias == 2  # no sigue contando por encima del hueco
    assert not r.entera


def test_racha_se_corta_si_no_cambia():
    assert calcular(_dias(100, 105, 105)) is None
    assert calcular(_dias(100, 100, 105)).dias == 1


def test_sin_dos_dias():
    assert calcular([]) is None
    assert calcular(_dias(100)) is None
    assert calcular([(HOY - timedelta(days=3), 100.0), (HOY, 110.0)]) is None


def test_formatear():
    r = Racha(True, 3, HOY - timedelta(days=3), 100, 110, True)

    texto = formatear_racha("bitcoin", r, "eur")

    assert (
        "🔺 <b>Bitcoin</b> lleva <b>3 días</b> seguidos subiendo, contando hoy" in texto
    )
    assert "+10.00% desde el 09/10: €100,00 → €110,00" in texto


def test_formatear_un_dia_y_sin_el_principio():
    texto = formatear_racha("solana", Racha(False, 1, HOY, 100, 95, False), "eur")

    assert "lleva <b>al menos 1 día</b> bajando" in texto
    assert "seguidos" not in texto
