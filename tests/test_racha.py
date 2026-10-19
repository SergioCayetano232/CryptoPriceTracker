"""Tests de /racha."""

from datetime import date, timedelta

import pytest

from crypto_tracker.alerts import formatear_racha
from crypto_tracker.racha import Racha, calcular, mas_larga

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


def test_mas_larga():
    dias = _dias(100, 101, 102, 103, 104, 90, 91, 92)

    assert mas_larga(dias, sube=True) == 4
    assert mas_larga(dias, sube=False) == 1


def test_mas_larga_se_corta_en_los_huecos_y_si_no_cambia():
    hueco = [(HOY - timedelta(days=10), 90.0), (HOY - timedelta(days=9), 95.0)]

    assert mas_larga([*hueco, *_dias(100, 101, 101, 102)], sube=True) == 1


def test_mas_larga_sin_dias():
    assert mas_larga([], sube=True) == 0


def test_formatear_con_una_mas_larga_antes():
    r = Racha(True, 3, HOY - timedelta(days=3), 100, 110, True)

    texto = formatear_racha("bitcoin", r, "eur", 7, date(2026, 7, 14))

    assert "La más larga subiendo desde el 14/07 fue de 7 días" in texto


def test_formatear_cuando_es_la_mas_larga():
    r = Racha(False, 5, HOY - timedelta(days=5), 100, 80, True)

    texto = formatear_racha("bitcoin", r, "eur", 5, date(2026, 7, 14))

    assert "🏆 Es la más larga bajando desde el 14/07" in texto


def test_formatear_sin_el_principio_no_compara():
    r = Racha(True, 3, HOY - timedelta(days=3), 100, 110, False)

    texto = formatear_racha("bitcoin", r, "eur", 3, date(2026, 7, 14))

    assert "más larga" not in texto
