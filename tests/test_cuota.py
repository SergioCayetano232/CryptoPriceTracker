"""Tests del contador de consultas a CoinGecko."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.cuota import (
    mensaje_aviso,
    mensaje_estado,
    mes,
    proyeccion,
    umbral_cruzado,
)


def _dia(dia, hora=12, mes_=10):
    return datetime(2026, mes_, dia, hora, tzinfo=timezone.utc)


def test_mes():
    assert mes(_dia(1)) == "2026-10"


def test_mes_en_utc():
    # las 00:30 del 1 en Madrid son aun el 30 de septiembre en UTC
    from datetime import timedelta

    madrid = timezone(timedelta(hours=2))
    assert mes(datetime(2026, 10, 1, 0, 30, tzinfo=madrid)) == "2026-09"


# --- cuando avisar ---


@pytest.mark.parametrize(
    "antes, total, umbral",
    [
        (7999, 8000, 0.8),
        (7998, 7999, None),
        (8000, 8001, None),  # ya pasado, no se repite
        (9999, 10000, 1.0),
        (7900, 10100, 1.0),  # si saltan dos de golpe, el mas alto
        (10500, 10501, None),
    ],
)
def test_umbral_cruzado(antes, total, umbral):
    assert umbral_cruzado(antes, total) == umbral


# --- a que ritmo vamos ---


def test_proyeccion_a_mitad_de_mes():
    # 1 de octubre a las 00:00 + 15,5 dias = la mitad de un mes de 31
    mitad = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)

    assert proyeccion(5000, mitad) == 10000


def test_proyeccion_el_primer_dia_no_dice_nada():
    assert proyeccion(50, _dia(1, hora=10)) is None


def test_proyeccion_en_diciembre():
    assert proyeccion(5000, datetime(2026, 12, 16, 12, tzinfo=timezone.utc)) == 10000


# --- los mensajes ---


def test_aviso_al_80_con_ritmo_alto():
    texto = mensaje_aviso(8000, 0.8, _dia(20))

    assert "Llevas 8.000 de las 10.000" in texto
    assert "(80%)" in texto
    assert "sube CHECK_INTERVAL" in texto


def test_aviso_al_80_con_ritmo_bueno():
    # 8.000 el dia 30 por la tarde: acabaria por debajo
    texto = mensaje_aviso(8000, 0.8, _dia(30, hora=23))

    assert "vas bien" in texto


def test_aviso_al_100():
    texto = mensaje_aviso(10000, 1.0, _dia(25))

    assert "hasta el día 1" in texto
    assert "A este ritmo" not in texto


def test_estado():
    texto = mensaje_estado(1234, _dia(10))

    assert "Llevas 1.234 de las 10.000" in texto
    assert "(12%)" in texto
    assert "vas bien" in texto


def test_estado_el_primer_dia_sin_ritmo():
    assert "ritmo" not in mensaje_estado(20, _dia(1, hora=3))
