"""Tests de /pizza."""

from datetime import date

from crypto_tracker.alerts import formatear_pizza
from crypto_tracker.pizza import Pizza

HOY = date(2026, 10, 25)


def test_cuentas():
    p = Pizza(82_000, HOY)

    assert p.total == 820_000_000
    assert p.por_pizza == 410_000_000


def test_aniversario():
    assert Pizza(1, HOY).aniversario == 209
    assert Pizza(1, date(2027, 5, 21)).aniversario == 1
    assert Pizza(1, date(2027, 5, 22)).aniversario == 0
    # Pasado el de este año, cuenta hasta el del que viene.
    assert Pizza(1, date(2027, 5, 23)).aniversario == 365


def test_formatear():
    texto = formatear_pizza(Pizza(82_000, HOY), "usd")

    assert "pagó <b>10.000 BTC</b> por dos pizzas" in texto
    assert "Hoy serían <b>$820 millones</b>, $410 millones cada una" in texto
    assert "Faltan 209 días para el Bitcoin Pizza Day" in texto


def test_formatear_el_dia():
    texto = formatear_pizza(Pizza(82_000, date(2027, 5, 22)), "eur")

    assert "🎉 Hoy es el Bitcoin Pizza Day" in texto
    assert "Faltan" not in texto
