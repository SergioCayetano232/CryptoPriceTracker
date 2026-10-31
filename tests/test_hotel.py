"""Tests de /hotel."""

from crypto_tracker.alerts import formatear_hotel
from crypto_tracker.hotel import Hotel


def test_cuantas():
    assert Hotel(1_000).noches == 10
    assert Hotel(100).noches == 1
    assert Hotel(99).noches == 0


def test_findes():
    assert Hotel(1_000).findes == 5
    assert Hotel(199).findes == 0
    assert Hotel(200).findes == 1


def test_formatear():
    texto = formatear_hotel(Hotel(1_050), "eur")

    assert "🏨 <b>Tu cartera en noches de hotel</b>" in texto
    assert "Vale €1.050,00" in texto
    assert "Te da para <b>10 noches</b>" in texto
    assert "Son 5 escapadas de finde, de viernes a domingo" in texto
    assert "<i>A unos €100 la noche, en habitación doble</i>" in texto


def test_formatear_miles():
    texto = formatear_hotel(Hotel(250_000), "eur")

    assert "<b>2.500 noches</b>" in texto
    assert "Son 1.250 escapadas" in texto


def test_formatear_una_escapada():
    assert "Es 1 escapada de finde" in formatear_hotel(Hotel(250), "eur")


def test_formatear_una_y_ninguna():
    texto = formatear_hotel(Hotel(150), "eur")
    assert "<b>1 noche</b>" in texto
    assert "Para un finde entero te falta otra" in texto

    texto = formatear_hotel(Hotel(60), "eur")
    assert "No te da ni para una noche 😅" in texto
    assert "finde" not in texto
