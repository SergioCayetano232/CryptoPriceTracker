"""Tests de /enletras."""

import pytest

from crypto_tracker.alerts import formatear_enletras
from crypto_tracker.comandos import interpretar
from crypto_tracker.enletras import dinero, letras


@pytest.mark.parametrize(
    "n, esperado",
    [
        (0, "cero"),
        (1, "un"),
        (16, "dieciséis"),
        (21, "veintiún"),
        (30, "treinta"),
        (45, "cuarenta y cinco"),
        (100, "cien"),
        (101, "ciento un"),
        (500, "quinientos"),
        (1000, "mil"),
        (2021, "dos mil veintiún"),
        (21_000, "veintiún mil"),
        (31_000, "treinta y un mil"),
        (100_000, "cien mil"),
        (1_000_000, "un millón"),
        (
            1_234_567,
            "un millón doscientos treinta y cuatro mil quinientos sesenta y siete",
        ),
        (21_000_000, "veintiún millones"),
    ],
)
def test_letras(n, esperado):
    assert letras(n) == esperado


@pytest.mark.parametrize(
    "valor, currency, esperado",
    [
        (1, "eur", "Un euro"),
        (1.01, "eur", "Un euro con un céntimo"),
        (1234.5, "eur", "Mil doscientos treinta y cuatro euros con cincuenta céntimos"),
        (2_000_000, "eur", "Dos millones de euros"),
        (1, "usd", "Un dólar"),
        (5, "gbp", "Cinco GBP"),
        (0.999, "eur", "Un euro"),
    ],
)
def test_dinero(valor, currency, esperado):
    assert dinero(valor, currency) == esperado


def test_formatear():
    texto = formatear_enletras(1234.5, "eur")

    assert texto.startswith("✍️ <b>Tu cartera, en letras</b>")
    assert "Mil doscientos treinta y cuatro euros con cincuenta céntimos" in texto
    assert "<i>€1.234,50</i>" in texto


def test_comando():
    assert interpretar("/enletras") == ("enletras", "")
    assert interpretar("/cheque") == ("enletras", "")
