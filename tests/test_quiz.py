"""Tests de /quiz."""

import random

import pytest

from crypto_tracker.alerts import formatear_quiz, formatear_respuesta_quiz
from crypto_tracker.comandos import interpretar as interpretar_comando
from crypto_tracker.quiz import PREGUNTAS, interpretar, sacar


def test_salen_todas():
    assert {sacar(random.Random(i)) for i in range(300)} == set(range(len(PREGUNTAS)))


def test_bien_hechas():
    for p in PREGUNTAS:
        assert len(set(p.opciones)) == 3
        assert 0 <= p.buena < 3


def test_la_buena_no_va_siempre_en_el_mismo_sitio():
    assert len({p.buena for p in PREGUNTAS}) == 3


@pytest.mark.parametrize(
    "argumento, esperado",
    [
        ("3 1", (3, 1)),
        ("", None),
        ("hola", None),
        ("3", None),
        ("99 0", None),
        ("3 5", None),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


def test_formatear_la_pregunta():
    texto, botones = formatear_quiz(1)

    assert texto == "❓ <b>¿Cuántos bitcoin habrá como mucho?</b>"
    assert botones == [
        [("21 millones", "/quiz 1 0")],
        [("100 millones", "/quiz 1 1")],
        [("No hay límite", "/quiz 1 2")],
    ]


def test_formatear_acierto():
    texto, botones = formatear_respuesta_quiz(1, 0)

    assert texto.startswith("✅ <b>¡Bien!</b>")
    assert "21 millones" in texto
    assert botones == [[("🎲 Otra pregunta", "/quiz")]]


def test_formatear_fallo():
    texto, _ = formatear_respuesta_quiz(1, 2)

    assert texto.startswith("❌ <b>Casi</b>")
    assert "Dijiste «No hay límite», era <b>21 millones</b>" in texto


def test_comando():
    assert interpretar_comando("/quiz") == ("quiz", "")
    assert interpretar_comando("/trivial") == ("quiz", "")
