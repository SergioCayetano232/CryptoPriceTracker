"""Tests de /mes."""

from datetime import datetime, timedelta

from crypto_tracker import mes
from crypto_tracker.alerts import formatear_semana
from crypto_tracker.config import parse_cartera
from crypto_tracker.semanal import semana


def _aqui(*args):
    return datetime(*args).astimezone()


def test_principio():
    assert mes.principio(_aqui(2026, 11, 15, 18, 30)) == _aqui(2026, 11, 1)


def test_el_mismo_dia_1():
    assert mes.principio(_aqui(2026, 11, 1, 0, 5)) == _aqui(2026, 11, 1)


def test_horas():
    assert mes.horas(_aqui(2026, 11, 3, 12)) == 60


def test_nombre():
    assert mes.nombre(_aqui(2026, 1, 20)) == "enero"
    assert mes.nombre(_aqui(2026, 12, 31, 23)) == "diciembre"


def test_formatear():
    inicio = _aqui(2026, 11, 1)
    filas = [
        (inicio, "bitcoin", 50000.0),
        (inicio + timedelta(days=4), "bitcoin", 55000.0),
    ]
    s = semana(parse_cartera("bitcoin:0.1"), filas)

    texto = formatear_semana(
        s, "eur", titulo="🗓️ <b>Tu noviembre</b>", tramo="en lo que va de mes"
    )

    assert "🗓️ <b>Tu noviembre</b>" in texto
    assert "Tu cartera vale <b>€5.500,00</b>" in texto
    assert "🔺 +10.00% (+€500,00) en lo que va de mes" in texto
    assert "semana" not in texto
