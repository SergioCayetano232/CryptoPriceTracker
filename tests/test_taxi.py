"""Tests de /taxi."""

from crypto_tracker.alerts import formatear_taxi
from crypto_tracker.taxi import Taxi


def test_cuantos():
    t = Taxi(1_000)

    assert t.viajes == 30
    assert t.escapadas == 15
    assert Taxi(32.99).viajes == 0


def test_formatear():
    texto = formatear_taxi(Taxi(1_000), "eur")

    assert "🚕 <b>Tu cartera en taxis al aeropuerto</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te da para <b>30 viajes</b>" in texto
    assert "Contando ida y vuelta, son 15 escapadas" in texto
    assert "<i>A €33 el viaje, la tarifa fija de Madrid a Barajas</i>" in texto


def test_formatear_miles():
    assert "<b>3.030 viajes</b>" in formatear_taxi(Taxi(100_000), "eur")


def test_formatear_impar():
    # 3 viajes son 1 escapada, el que sobra no cuenta
    assert "son 1 escapada\n" in formatear_taxi(Taxi(100), "eur")


def test_formatear_solo_ida():
    texto = formatear_taxi(Taxi(40), "eur")

    assert "<b>1 viaje</b>" in texto
    assert "Solo la ida, la vuelta en metro" in texto


def test_formatear_ninguno():
    texto = formatear_taxi(Taxi(20), "eur")

    assert "No te da ni para un taxi 😅" in texto
    assert "ida" not in texto
