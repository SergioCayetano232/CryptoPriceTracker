"""Tests de /cana."""

from crypto_tracker.alerts import formatear_cana
from crypto_tracker.cana import Cana


def test_cuantas():
    c = Cana(100)

    assert c.cuantas == 33
    assert c.rondas == 8


def test_no_llega_a_una():
    assert Cana(2.5).cuantas == 0


def test_formatear():
    texto = formatear_cana(Cana(2_000), "eur")

    assert "🍺 <b>Tu cartera en cañas</b>" in texto
    assert "Vale €2.000,00" in texto
    assert "Te da para <b>666 cañas</b>" in texto
    assert "Si invitas tú, 166 rondas para cuatro" in texto
    assert "<i>A unos €3 cada una</i>" in texto


def test_formatear_una_y_ninguna():
    texto = formatear_cana(Cana(3), "eur")
    assert "<b>1 caña</b>" in texto
    assert "rondas" not in texto
    assert "No te da ni para una caña 😅" in formatear_cana(Cana(1), "eur")


def test_formatear_una_ronda():
    assert "Si invitas tú, 1 ronda para cuatro" in formatear_cana(Cana(12), "eur")
