"""Tests de a que precio salta el siguiente aviso."""

import pytest

from crypto_tracker.alerts import revisar
from crypto_tracker.config import Watch
from crypto_tracker.proximo import objetivos

PCT = Watch("bitcoin", percent=5)
PASO = Watch("bitcoin", step=1000)
RANGO = Watch("bitcoin", 55000, 75000)


def test_porcentaje_desde_el_ultimo_aviso():
    assert objetivos(PCT, "%60000.0", 61000) == pytest.approx((63000, 57000))


def test_paso_el_siguiente_multiplo_y_el_suyo():
    assert objetivos(PASO, "63000.0", 63568) == (64000, 63000)


def test_rango_dentro():
    assert objetivos(RANGO, "normal", 63000) == (75000, 55000)


def test_rango_por_encima_solo_queda_abajo():
    assert objetivos(RANGO, "alto", 76000) == (None, 55000)


def test_rango_de_un_solo_lado():
    assert objetivos(Watch("ethereum", max_price=4000), "normal", 2500) == (4000, None)


@pytest.mark.parametrize(
    "watch, referencia",
    [
        (PCT, None),  # recien puesta
        (PCT, "63000.0"),  # venia de pasos y aun no ha pasado un ciclo
        (PASO, None),
        (PASO, "normal"),
    ],
)
def test_sin_referencia_no_inventa(watch, referencia):
    assert objetivos(watch, referencia, 63000) == (None, None)


@pytest.mark.parametrize(
    "watch, referencia, precio",
    [
        (PCT, "%60000.0", 61000),
        (PASO, "63000.0", 63568),
        (RANGO, "normal", 63000),
    ],
)
def test_cuadra_con_los_avisos_de_verdad(watch, referencia, precio):
    # Justo en el objetivo avisa y un pelo antes no: lo que dice /status es
    # lo que hace el bot.
    arriba, abajo = objetivos(watch, referencia, precio)
    estado = {"bitcoin": referencia}

    assert revisar({"bitcoin": arriba * 1.0001}, [watch], estado)[0]
    assert not revisar({"bitcoin": arriba * 0.9999}, [watch], estado)[0]
    assert revisar({"bitcoin": abajo * 0.9999}, [watch], estado)[0]
    assert not revisar({"bitcoin": abajo * 1.0001}, [watch], estado)[0]
