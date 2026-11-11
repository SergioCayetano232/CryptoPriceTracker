"""Tests del aviso de las estables que se salen de su dólar."""

import pytest

from crypto_tracker.alerts import formatear_estable
from crypto_tracker.estables import Desvio, de_las_tuyas, revisar


def test_solo_las_estables_y_sin_repetir():
    assert de_las_tuyas(["bitcoin", "tether", "dai", "tether"]) == ["tether", "dai"]


@pytest.mark.parametrize("precio", [0.99, 0.985, 1.01, 1.02])
def test_se_sale(precio):
    salen, vuelven = revisar({"tether": precio}, set())

    assert [d.coin_id for d in salen] == ["tether"]
    assert vuelven == []


@pytest.mark.parametrize("precio", [1.0, 0.995, 1.004])
def test_dentro_no_avisa(precio):
    assert revisar({"tether": precio}, set()) == ([], [])


def test_ya_avisada_no_repite():
    assert revisar({"tether": 0.97}, {"tether"}) == ([], [])


def test_vuelve_solo_si_se_acerca_de_verdad():
    # Al 0,8% sigue fuera: si no, rondando el 1% avisaría a ratos.
    assert revisar({"tether": 0.992}, {"tether"}) == ([], [])

    salen, vuelven = revisar({"tether": 0.998}, {"tether"})

    assert salen == []
    assert [d.coin_id for d in vuelven] == ["tether"]


def test_las_que_no_son_estables_no_cuentan():
    assert revisar({"bitcoin": 0.5}, set()) == ([], [])


def test_formatear_sale():
    texto = formatear_estable(Desvio("usd-coin", 0.9712))

    assert texto.startswith("⚠️ <b>USDC se sale de su dólar</b>\n")
    assert "Está a <b>$0,9712</b>, un <b>-2.88%</b>" in texto
    assert "cuando vuelva" in texto


def test_formatear_vuelve():
    texto = formatear_estable(Desvio("tether", 0.9991), vuelve=True)

    assert texto == "✅ <b>USDT</b> vuelve a su dólar: está a $0,9991 (-0.09%)"
