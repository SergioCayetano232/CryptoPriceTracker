"""Tests de /plan."""

from datetime import date

import pytest

from crypto_tracker.alerts import formatear_plan
from crypto_tracker.plan import Peticion, PlanError, calcular, cuanto, interpretar

HOY = date(2026, 11, 11)


def test_sin_interes_son_cuentas():
    c = calcular(Peticion(10000, 50))

    assert c.veces == 200
    assert c.dias == 1400
    assert c.metido == 10000
    assert c.intereses == pytest.approx(0)


def test_cuenta_lo_que_ya_tienes():
    c = calcular(Peticion(10000, 50), inicio=1000)

    assert c.veces == 180
    assert c.metido == 9000


def test_con_interes_llega_antes():
    c = calcular(Peticion(10000, 200, "mensual", 8))

    assert c.veces < 50
    assert c.final >= 10000
    assert c.intereses > 0
    assert c.final == pytest.approx(c.metido + c.intereses)


def test_el_interes_del_tramo_da_el_anual():
    # 1.000 al 10% sin meter nada más: al cabo de un año, 1.100.
    c = calcular(Peticion(1100, 0.0000001, "mensual", 10), inicio=1000)

    assert c.veces == 12


def test_ya_esta():
    c = calcular(Peticion(1000, 50), inicio=2000)

    assert c.veces == 0


def test_perdiendo_no_llega():
    c = calcular(Peticion(100000, 50, "semanal", -20))

    assert c.veces is None
    assert c.dias is None


def test_fecha():
    assert calcular(Peticion(700, 100)).fecha(HOY) == date(2026, 12, 30)


@pytest.mark.parametrize(
    "dias,texto",
    [
        (1, "1 día"),
        (7, "7 días"),
        (21, "3 semanas"),
        (90, "3 meses"),
        (365, "1 año"),
        (400, "1 año y 1 mes"),
        (1400, "3 años y 10 meses"),
    ],
)
def test_cuanto(dias, texto):
    assert cuanto(dias) == texto


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("10000 50", Peticion(10000, 50)),
        ("10k 50 € mensual", Peticion(10000, 50, "mensual")),
        ("10000 50 semanal al 8%", Peticion(10000, 50, "semanal", 8)),
        ("10000 5 7,5% diario", Peticion(10000, 5, "diario", 7.5)),
    ],
)
def test_interpretar(texto, esperado):
    assert interpretar(texto) == esperado


@pytest.mark.parametrize(
    "texto,error",
    [
        ("", "Escríbelo así"),
        ("10000", "Escríbelo así"),
        ("mucho 50", "no es una cifra"),
        ("10000 0", "no es lo que metes"),
        ("10000 50 anual", "No entiendo 'anual'"),
        ("10000 50 -100%", "no tiene sentido"),
    ],
)
def test_interpretar_mal(texto, error):
    with pytest.raises(PlanError, match=error):
        interpretar(texto)


def test_formatear():
    texto = formatear_plan(calcular(Peticion(10000, 50)), "eur", HOY)

    assert texto.startswith("🗓️ <b>Hacia €10.000,00</b>\n\n")
    assert (
        "Metiendo €50,00 cada semana, llegas en <b>3 años y 10 meses</b>, "
        "hacia septiembre de 2030"
    ) in texto
    assert "Habrás metido €10.000,00" in texto
    assert "cartera" not in texto
    assert "línea recta" not in texto


def test_formatear_con_interes_y_cartera():
    c = calcular(Peticion(10000, 200, "mensual", 8), inicio=500)

    texto = formatear_plan(c, "eur", HOY)

    assert "y el 8% al año pone €" in texto
    assert "Contando los €500,00 que ya tienes en cartera" in texto
    assert "línea recta" in texto


def test_formatear_ya_esta():
    texto = formatear_plan(calcular(Peticion(1000, 50), 2000), "eur", HOY)

    assert texto == "🎉 Ya está: tu cartera vale €2.000,00, más que €1.000,00"


def test_formatear_no_llega():
    c = calcular(Peticion(100000, 50, "semanal", -20))

    texto = formatear_plan(c, "eur", HOY)

    assert "no llegas a €100.000,00 ni en 100 años" in texto
    assert "Perdiendo un 20% al año" in texto
