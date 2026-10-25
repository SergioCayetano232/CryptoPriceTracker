"""Tests de /millonario."""

import pytest

from crypto_tracker.alerts import formatear_millonario
from crypto_tracker.millonario import Millonario, cantidad
from crypto_tracker.simbolos import de_id


def test_cuentas():
    m = Millonario(80_000, 0.5)

    assert m.necesitas == 12.5
    assert m.hecho == pytest.approx(4)


def test_sin_cartera():
    assert Millonario(80_000).hecho is None
    assert Millonario(80_000, 0).hecho is None


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (12.5, "12,5"),
        (12.16412, "12,1641"),
        (1.0, "1"),
        (406.9, "406,9"),
        (45_871_559.6, "45.871.560"),
    ],
)
def test_cantidad(valor, esperado):
    assert cantidad(valor) == esperado


def test_simbolo_de_id():
    assert de_id("bitcoin") == "BTC"
    assert de_id("pepe") is None


def test_formatear():
    texto = formatear_millonario("bitcoin", "BTC", Millonario(80_000, 0.5), "usd")

    assert "💰 <b>Para tener un millón en Bitcoin</b>" in texto
    assert "Necesitas <b>12,5 BTC</b>, a $80.000,00 cada uno" in texto
    assert "Con lo que tienes (0,5 BTC) llevas el <b>4.00%</b>" in texto


def test_formatear_sin_cartera():
    texto = formatear_millonario("bitcoin", "BTC", Millonario(80_000), "eur")

    assert "Con lo que tienes" not in texto
