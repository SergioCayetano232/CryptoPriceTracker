"""Tests de /libro."""

from crypto_tracker.alerts import formatear_libro
from crypto_tracker.libro import Libro


def test_cuantos():
    assert Libro(100).libros == 5
    assert Libro(20).libros == 1
    assert Libro(19).libros == 0


def test_formatear():
    texto = formatear_libro(Libro(1_000), "eur")

    assert "📚 <b>Tu cartera en libros</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te da para <b>50 libros</b>" in texto
    assert "Leyendo uno al mes, tienes para 4 años y pico" in texto
    assert "<i>A unos €20 el libro</i>" in texto


def test_formatear_años_justos():
    assert "tienes para 2 años\n" in formatear_libro(Libro(480), "eur")


def test_formatear_menos_de_un_año():
    texto = formatear_libro(Libro(200), "eur")

    assert "<b>10 libros</b>" in texto
    assert "tienes para 10 meses" in texto


def test_formatear_uno_y_ninguno():
    texto = formatear_libro(Libro(20), "eur")
    assert "<b>1 libro</b>" in texto
    assert "tienes para 1 mes" in texto
    texto = formatear_libro(Libro(10), "eur")
    assert "No te da ni para un libro 😅" in texto
    assert "al mes" not in texto
