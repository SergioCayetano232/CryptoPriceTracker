"""Tests de /spotify."""

from crypto_tracker.alerts import formatear_spotify
from crypto_tracker.spotify import Spotify


def test_cuantos():
    assert Spotify(100).meses == 8
    assert Spotify(11.99).meses == 1
    assert Spotify(10).meses == 0


def test_formatear():
    texto = formatear_spotify(Spotify(1_000), "eur")

    assert "🎧 <b>Tu cartera en Spotify</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te paga <b>83 meses</b>, más de 6 años" in texto
    assert "<i>A €11,99 al mes, el Premium Individual</i>" in texto


def test_formatear_ni_uno():
    assert "No te paga ni un mes 😅" in formatear_spotify(Spotify(10), "eur")
