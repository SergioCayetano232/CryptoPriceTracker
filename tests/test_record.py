"""Tests de /record."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.alerts import formatear_record
from crypto_tracker.record import SIN_LIMITE, Record, calcular, horas

INICIO = datetime(2026, 8, 7, 10, tzinfo=timezone.utc)


def _serie(*valores):
    return [(INICIO + timedelta(days=i), v) for i, v in enumerate(valores)]


def test_calcular():
    r = calcular(_serie(1000, 1500, 1200, 1100))

    assert r.maximo == 1500
    assert r.cuando == INICIO + timedelta(days=1)
    assert r.ahora == 1100
    assert r.desde == INICIO
    assert r.falta == 400
    assert r.caida == pytest.approx(-26.667, abs=0.001)
    assert not r.en_record


def test_con_empate_cuenta_la_primera_vez():
    assert calcular(_serie(1000, 1500, 1500, 900)).cuando == INICIO + timedelta(days=1)


def test_en_record():
    assert calcular(_serie(1000, 1200, 1300)).en_record


def test_sin_datos():
    assert calcular([]) is None
    assert calcular(_serie(1000)) is None


def test_horas():
    assert horas(90) == 90 * 24
    assert horas(0) == SIN_LIMITE


def test_formatear():
    texto = formatear_record(
        Record(1500, INICIO + timedelta(days=1), 1100, INICIO), "eur"
    )

    assert "🏆 <b>El récord de tu cartera</b>" in texto
    assert "<b>€1.500,00</b>, el 08/08/2026" in texto
    assert "Ahora vale €1.100,00: 🔻 -26.67%" in texto
    assert "le faltan <b>€400,00</b> para volver" in texto
    assert "Con lo que tienes hoy" in texto
    assert "desde el 07/08/2026" in texto


def test_formatear_en_record():
    texto = formatear_record(Record(1300, INICIO, 1300, INICIO), "eur")

    assert "🎉 Lo tienes ahora mismo: <b>€1.300,00</b>" in texto
    assert "faltan" not in texto
