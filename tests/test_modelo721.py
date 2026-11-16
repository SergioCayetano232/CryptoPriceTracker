"""Tests del modelo 721."""

from datetime import date, datetime, timedelta, timezone

import pytest

from crypto_tracker.config import Posicion
from crypto_tracker.modelo721 import (
    calcular,
    cartera_en,
    cierre,
    en_plazo,
    horas_desde,
    toca_avisar,
)
from crypto_tracker.movimientos import Movimiento

FIN = cierre(2025)


def _mov(coin_id, antes, dias_despues, tipo="compra"):
    cuando = FIN + timedelta(days=dias_despues)
    return Movimiento(1, coin_id, tipo, 1, 100, antes, cuando)


@pytest.mark.parametrize(
    "dia, sale",
    [
        (date(2026, 1, 1), True),
        (date(2026, 3, 31), True),
        (date(2026, 4, 1), False),
        (date(2026, 12, 31), False),
    ],
)
def test_en_plazo(dia, sale):
    assert en_plazo(dia) is sale


def test_cierre_es_medianoche_en_españa():
    assert FIN.astimezone(timezone(timedelta(hours=1))).strftime("%H:%M") == "23:59"


def test_en_plazo_mira_el_31_de_diciembre():
    m = calcular(40000, 60000, date(2026, 3, 1))

    assert m.en_plazo
    assert m.año == 2025
    assert m.dias == 30
    assert m.toca


def test_justo_50000_no_toca():
    # Tiene que pasar de 50.000, no llegar.
    assert not calcular(0, 50000, date(2026, 1, 10)).toca


def test_fuera_de_plazo_mira_lo_de_este_año():
    m = calcular(45000, 60000, date(2026, 11, 16))

    assert not m.en_plazo
    assert m.cierre is None
    assert m.año == 2026
    assert m.falta == 5000
    assert m.dias == 135
    assert not m.toca


def test_cartera_sin_movimientos_despues():
    ahora = [Posicion("bitcoin", 1, 100)]

    assert cartera_en(ahora, [_mov("bitcoin", None, -10)], FIN) == ahora


def test_cartera_deshace_lo_de_despues():
    ahora = [Posicion("bitcoin", 2, 200), Posicion("solana", 5, 50)]
    movimientos = [
        _mov("bitcoin", Posicion("bitcoin", 1.5, 150), 20),
        _mov("bitcoin", Posicion("bitcoin", 1, 100), 3),  # la primera manda
        _mov("solana", None, 5),  # no la tenías
        _mov("ethereum", Posicion("ethereum", 3, 300), 8, "venta"),  # la vendiste
    ]

    sale = sorted(cartera_en(ahora, movimientos, FIN), key=lambda p: p.coin_id)

    assert sale == [Posicion("bitcoin", 1, 100), Posicion("ethereum", 3, 300)]


@pytest.mark.parametrize(
    "valor, avisado, sale",
    [
        (None, None, False),
        (50000, None, False),
        (50001, None, True),
        (60000, date(2026, 2, 1), False),  # ya se avisó este año
        (60000, date(2025, 12, 1), True),
    ],
)
def test_toca_avisar(valor, avisado, sale):
    assert toca_avisar(valor, avisado, date(2026, 11, 16)) is sale


def test_horas_desde():
    ahora = datetime(2026, 1, 2, 22, 59, tzinfo=timezone.utc)

    assert horas_desde(FIN, ahora) == 48
