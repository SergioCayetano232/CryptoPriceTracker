"""Tests de /zapatillas."""

from crypto_tracker.alerts import formatear_zapatillas
from crypto_tracker.zapatillas import Zapatillas


def test_cuantos():
    z = Zapatillas(1_000)

    assert z.pares == 8
    assert z.años == 2


def test_no_llega_a_un_par():
    assert Zapatillas(119).pares == 0


def test_formatear():
    texto = formatear_zapatillas(Zapatillas(1_000), "eur")

    assert "👟 <b>Tu cartera en zapatillas</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te da para <b>8 pares</b>" in texto
    assert "Estrenando unas cada temporada, vas calzado 2 años" in texto
    assert "<i>A unos €120 el par</i>" in texto


def test_formatear_menos_de_un_año():
    texto = formatear_zapatillas(Zapatillas(360), "eur")

    assert "<b>3 pares</b>" in texto
    assert "temporada" not in texto


def test_formatear_uno_y_ninguno():
    texto = formatear_zapatillas(Zapatillas(500), "eur")
    assert "vas calzado 1 año" in texto
    assert "<b>1 par</b>" in formatear_zapatillas(Zapatillas(120), "eur")
    texto = formatear_zapatillas(Zapatillas(50), "eur")
    assert "No te da ni para un par 😅" in texto
