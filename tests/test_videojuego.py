"""Tests de /videojuego."""

import pytest

from crypto_tracker.alerts import formatear_videojuego
from crypto_tracker.videojuego import Videojuego


def test_cuantos():
    v = Videojuego(3_000)

    assert v.juegos == 37
    assert v.años == pytest.approx(3.083, abs=0.001)
    assert Videojuego(79.99).juegos == 0


def test_formatear():
    texto = formatear_videojuego(Videojuego(3_000), "eur")

    assert "🎮 <b>Tu cartera en videojuegos</b>" in texto
    assert "Vale €3.000,00" in texto
    assert "Te da para <b>37 juegos</b>" in texto
    assert "Comprando uno al mes, tienes para 3,1 años" in texto
    assert "<i>A unos €80 el juego, recién salido</i>" in texto


def test_formatear_un_año_justo():
    # 12 juegos, sin "1,0 años"
    texto = formatear_videojuego(Videojuego(960), "eur")

    assert "tienes para 1 año\n" in texto


def test_formatear_miles():
    assert "<b>1.250 juegos</b>" in formatear_videojuego(Videojuego(100_000), "eur")


def test_formatear_menos_de_un_año():
    texto = formatear_videojuego(Videojuego(400), "eur")

    assert "<b>5 juegos</b>" in texto
    assert "tienes para 5 meses" in texto


def test_formatear_uno_y_ninguno():
    texto = formatear_videojuego(Videojuego(100), "eur")
    assert "<b>1 juego</b>" in texto
    assert "tienes para 1 mes" in texto

    texto = formatear_videojuego(Videojuego(50), "eur")
    assert "No te da ni para un juego 😅" in texto
    assert "al mes" not in texto
