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


def test_principio_tras_el_cambio_de_hora():
    # Octubre empieza en horario de verano y el 30 ya es de invierno.
    assert mes.principio(_aqui(2026, 10, 30, 12)) == _aqui(2026, 10, 1)
    assert (
        mes.principio(_aqui(2026, 10, 30, 12)).utcoffset()
        == _aqui(2026, 10, 1).utcoffset()
    )


def test_principio_del_ano():
    assert mes.principio_del_ano(_aqui(2026, 7, 15, 9)) == _aqui(2026, 1, 1)


def test_horas_del_ano():
    assert mes.horas_del_ano(_aqui(2026, 1, 3)) == 48


def test_pista_si_borra_antes():
    texto = mes.pista(90, 200 * 24)

    assert "Solo guardo 90 días" in texto
    assert "HISTORY_DAYS=366" in texto


def test_sin_pista_si_le_da_o_no_borra():
    assert mes.pista(366, 200 * 24) is None
    assert mes.pista(0, 200 * 24) is None


def test_formatear_con_pista():
    inicio = _aqui(2026, 3, 1)
    filas = [
        (inicio, "bitcoin", 50000.0),
        (inicio + timedelta(days=4), "bitcoin", 55000.0),
    ]
    s = semana(parse_cartera("bitcoin:0.1"), filas)

    texto = formatear_semana(s, "eur", desde=inicio, pista="Sube HISTORY_DAYS")

    assert "Solo tengo precios desde el 01/03" in texto
    assert "<i>Sube HISTORY_DAYS</i>" in texto
    assert "Sube" not in formatear_semana(s, "eur", pista="Sube HISTORY_DAYS")
