"""Tests de la línea de contexto de los avisos."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker.avisos.contexto import Contexto, buscar

# A mediodía: así la hora de aquí no cambia el día.
INICIO = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


def _diaria(*precios):
    return [(INICIO + timedelta(days=i), p) for i, p in enumerate(precios)]


def _bajada_y_rebote(rebote):
    """Cae un 10% en un día y a la semana está a `rebote`."""
    return [100, 90, 90, 90, 90, 90, 90, 90, rebote]


def test_buscar_tres_bajadas_que_rebotan():
    serie = _diaria(*_bajada_y_rebote(99), *_bajada_y_rebote(99), *_bajada_y_rebote(81))

    c = buscar(serie, -8)

    assert c == Contexto(
        sube=False,
        desde=pytest.approx(6.4),
        veces=3,
        media=pytest.approx((10 + 10 - 10) / 3),
        siguio=1,
        dias=27,
    )


def test_movimiento_pequeño_no_busca():
    serie = _diaria(*_bajada_y_rebote(99) * 3)

    assert buscar(serie, -2) is None


def test_pocas_veces_no_dice_nada():
    serie = _diaria(*_bajada_y_rebote(99) * 2)

    assert buscar(serie, -8) is None


def test_no_mezcla_subidas_con_bajadas():
    serie = _diaria(*_bajada_y_rebote(99) * 3)

    assert buscar(serie, 8) is None


def test_lo_mucho_menor_no_cuenta_como_parecido():
    # Caídas del 10% no son "como" una del 20%.
    serie = _diaria(*_bajada_y_rebote(99) * 3)

    assert buscar(serie, -20) is None


def test_una_racha_cuenta_una_vez():
    # Cuatro días seguidos cayendo un 10%: una sola vez, no cuatro.
    racha = [100, 90, 81, 72.9, 65.6, 65.6, 65.6, 65.6, 65.6, 65.6, 65.6, 65.6]
    serie = _diaria(*racha, *_bajada_y_rebote(99) * 2)

    c = buscar(serie, -10)

    assert c.veces == 3


def test_sin_semana_detras_no_cuenta():
    # La última caída no tiene aún 7 días detrás.
    serie = _diaria(*_bajada_y_rebote(99) * 3, 100, 90)

    assert buscar(serie, -8).veces == 3


def test_salta_huecos_del_bot_apagado():
    # Si falta el día de antes, el salto no es de un día.
    serie = _diaria(*_bajada_y_rebote(99) * 3)
    del serie[8]

    assert buscar(serie, -8) is None
