"""Tests del resumen de la semana."""

from datetime import date, datetime, time, timedelta, timezone

import pytest

from crypto_tracker.alerts import formatear_semana
from crypto_tracker.config import Posicion
from crypto_tracker.semanal import Semana, semana, toca

INICIO = datetime(2026, 9, 27, 9, 0, tzinfo=timezone.utc)


def _filas(*tandas):
    """Cada tanda son los precios de una consulta, un dia despues de la anterior."""
    filas = []
    for i, precios in enumerate(tandas):
        cuando = INICIO + timedelta(days=i)
        filas += [(cuando, c, p) for c, p in precios.items()]
    return filas


CARTERA = [Posicion("bitcoin", 0.1, 5000.0), Posicion("solana", 10.0, 1000.0)]


def test_la_semana_de_la_cartera():
    filas = _filas(
        {"bitcoin": 60000.0, "solana": 100.0},
        {"bitcoin": 63000.0, "solana": 95.0},
    )

    s = semana(CARTERA, filas)

    assert s.inicio == pytest.approx(7000.0)
    assert s.fin == pytest.approx(7250.0)
    assert s.ganancia == pytest.approx(250.0)
    assert s.porcentaje == pytest.approx(3.5714, abs=0.001)


def test_de_mejor_a_peor():
    filas = _filas(
        {"bitcoin": 60000.0, "solana": 100.0},
        {"bitcoin": 63000.0, "solana": 95.0},
    )

    cambios = semana(CARTERA, filas).cambios

    assert [c for c, _ in cambios] == ["bitcoin", "solana"]
    assert cambios[0][1] == pytest.approx(5.0)
    assert cambios[1][1] == pytest.approx(-5.0)


def test_lo_que_no_es_tuyo_no_cuenta():
    filas = _filas(
        {"bitcoin": 60000.0, "solana": 100.0, "pepe": 1.0},
        {"bitcoin": 63000.0, "solana": 95.0, "pepe": 2.0},
    )

    assert "pepe" not in dict(semana(CARTERA, filas).cambios)


def test_sin_datos_no_hay_semana():
    assert semana(CARTERA, []) is None
    assert semana(CARTERA, _filas({"bitcoin": 60000.0, "solana": 100.0})) is None


def test_solo_los_domingos():
    domingo = datetime(2026, 10, 4, 9, 30).astimezone()
    lunes = datetime(2026, 10, 5, 9, 30).astimezone()

    assert toca(domingo, time(9), None) is True
    assert toca(lunes, time(9), None) is False
    # ya mandado hoy
    assert toca(domingo, time(9), date(2026, 10, 4)) is False


def test_mensaje_de_la_semana():
    s = Semana(
        [(INICIO, 7000.0), (INICIO, 7250.0)],
        [("bitcoin", 5.0), ("solana", -5.0)],
    )

    texto = formatear_semana(s, "eur")

    assert "Tu cartera vale <b>€7.250,00</b>" in texto
    assert "🔺 +3.57% (+€250,00) en la semana" in texto
    assert texto.index("Bitcoin") < texto.index("Solana")
    assert "Solo tengo precios" not in texto


def test_mensaje_de_una_semana_mala():
    s = Semana([(INICIO, 7000.0), (INICIO, 6500.0)], [])

    assert "🔻 -7.14% (-€500,00)" in formatear_semana(s, "eur")


def test_mensaje_avisa_si_falta_el_principio():
    s = Semana([(INICIO, 7000.0), (INICIO, 7250.0)], [])

    assert "Solo tengo precios desde" in formatear_semana(s, "eur", desde=INICIO)
