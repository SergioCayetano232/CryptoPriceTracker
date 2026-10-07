"""Tests de los comandos de Telegram."""

import pytest

from crypto_tracker.comandos import (
    AYUDA,
    COMANDOS,
    NO_ENTIENDO,
    interpretar,
    no_entiendo,
)


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("/status", ("status", "")),
        ("/mute 2h", ("mute", "2h")),
        ("  /MUTE   30m ", ("mute", "30m")),
        ("/historico bitcoin", ("historico", "bitcoin")),
        ("/status@MiBot", ("status", "")),  # asi llega en los grupos
        ("/mute@MiBot 1d", ("mute", "1d")),
        ("/start", ("ayuda", "")),
        ("/help", ("ayuda", "")),
        ("/history ethereum", ("historico", "ethereum")),
        ("/inventado", ("inventado", "")),  # se decide luego que no existe
    ],
)
def test_interpretar(texto, esperado):
    assert interpretar(texto) == esperado


@pytest.mark.parametrize("texto", ["", "   ", "hola", "status", "precio /status"])
def test_lo_que_no_es_comando(texto):
    assert interpretar(texto) is None


def test_la_ayuda_lista_todos_los_comandos():
    for nombre in COMANDOS:
        assert f"/{nombre}" in AYUDA


@pytest.mark.parametrize(
    "nombre,argumento,esperado",
    [
        ("preico", "btc", "/precio btc"),
        ("satus", "", "/status"),
        ("alertass", "", "/alertas"),
        ("histroy", "eth 7d", "/historico eth 7d"),  # el alias lleva al comando
    ],
)
def test_no_entiendo_sugiere_el_parecido(nombre, argumento, esperado):
    assert no_entiendo(nombre, argumento).endswith(f"¿Querías decir {esperado}?")


@pytest.mark.parametrize("nombre", ["xyzzy", "bailar", "borrar", "hola"])
def test_no_entiendo_sin_nada_parecido(nombre):
    assert no_entiendo(nombre) == NO_ENTIENDO
