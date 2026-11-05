"""Tests de /ppt."""

import random

import pytest

from crypto_tracker.alerts import formatear_ppt
from crypto_tracker.ppt import PptError, interpretar, resultado, sacar


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("piedra", "piedra"),
        ("PAPEL", "papel"),
        ("tijeras", "tijera"),
        ("✊", "piedra"),
        ("✋", "papel"),
        ("✌️", "tijera"),
        ("✌", "tijera"),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


@pytest.mark.parametrize("argumento", ["", "lagarto", "piedra papel"])
def test_interpretar_mal(argumento):
    with pytest.raises(PptError, match="/ppt piedra"):
        interpretar(argumento)


def test_salen_las_tres():
    assert {sacar(random.Random(i)) for i in range(50)} == {"piedra", "papel", "tijera"}


@pytest.mark.parametrize(
    "tuya,del_bot,esperado",
    [
        ("piedra", "tijera", "ganas"),
        ("papel", "piedra", "ganas"),
        ("tijera", "papel", "ganas"),
        ("piedra", "papel", "pierdes"),
        ("papel", "tijera", "pierdes"),
        ("tijera", "piedra", "pierdes"),
        ("papel", "papel", "empate"),
    ],
)
def test_resultado(tuya, del_bot, esperado):
    assert resultado(tuya, del_bot) == esperado


def test_formatear():
    texto = formatear_ppt("piedra", "tijera", "ganas")

    assert texto.startswith("Tú ✊ piedra · yo ✌️ tijera")
    assert "<b>Ganas tú: compra" in texto
    assert "No es un consejo" in texto


def test_formatear_empate():
    assert "HODL" in formatear_ppt("papel", "papel", "empate")
