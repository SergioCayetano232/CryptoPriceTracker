"""Tests de /concierto."""

from crypto_tracker.alerts import formatear_concierto
from crypto_tracker.concierto import Concierto


def test_cuantas():
    c = Concierto(1_000)

    assert c.entradas == 20
    assert c.para_dos == 10


def test_no_llega_a_una():
    assert Concierto(49).entradas == 0


def test_formatear():
    texto = formatear_concierto(Concierto(1_000), "eur")

    assert "🎤 <b>Tu cartera en conciertos</b>" in texto
    assert "Vale €1.000,00" in texto
    assert "Te da para <b>20 entradas</b>" in texto
    assert "Si invitas tú, 10 conciertos para dos" in texto
    assert "<i>A unos €50 la entrada</i>" in texto


def test_formatear_impar():
    # La entrada que sobra no da para ir acompañado
    assert "Si invitas tú, 1 concierto para dos" in formatear_concierto(
        Concierto(150), "eur"
    )


def test_formatear_una_y_ninguna():
    texto = formatear_concierto(Concierto(50), "eur")
    assert "<b>1 entrada</b>" in texto
    assert "invitas" not in texto
    texto = formatear_concierto(Concierto(20), "eur")
    assert "No te da ni para una entrada 😅" in texto
