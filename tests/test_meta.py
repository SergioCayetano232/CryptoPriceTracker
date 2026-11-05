"""Tests de /meta."""

import pytest

from crypto_tracker.alerts import formatear_meta
from crypto_tracker.meta import Meta, MetaError, interpretar


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("10000", 10000),
        ("10k", 10000),
        ("10.000", 10000),
        ("10.000 €", 10000),
        ("2500,50€", 2500.5),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


@pytest.mark.parametrize("argumento", ["", "mucho", "0", "-5", "10 20"])
def test_interpretar_mal(argumento):
    with pytest.raises(MetaError, match="/meta 10000"):
        interpretar(argumento)


def test_cuentas():
    m = Meta(2500, 10000)

    assert m.falta == 7500
    assert m.cambio == pytest.approx(300)
    assert m.veces == 4
    assert m.hecho == 25


def test_pasada_la_meta_la_barra_no_se_sale():
    assert Meta(12000, 10000).hecho == 100


def test_formatear():
    texto = formatear_meta(Meta(2500, 10000), "eur")

    assert "🏁 <b>Tu cartera hacia €10.000,00</b>" in texto
    assert "Vale €2.500,00" in texto
    assert "25% del camino" in texto
    assert "Te faltan <b>€7.500,00</b>: tiene que subir un <b>+300.00%</b>" in texto
    assert "multiplicarse por 4,0" in texto


def test_formatear_cerca_no_dice_lo_de_multiplicar():
    texto = formatear_meta(Meta(9000, 10000), "eur")

    assert "+11.11%" in texto
    assert "multiplicarse" not in texto


def test_formatear_ya_llegaste():
    texto = formatear_meta(Meta(12000, 10000), "eur")

    assert "🎉 Ya está: vale €12.000,00, €2.000,00 por encima" in texto
    assert "faltan" not in texto
