"""Tests de los comandos de Telegram."""

import pytest

from crypto_tracker.comandos import (
    AYUDA,
    COMANDOS,
    EJEMPLOS,
    NO_ENTIENDO,
    ayuda,
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
        ("/estado", ("status", "")),
        ("/p btc eth", ("precio", "btc eth")),
        ("/callar 2h", ("mute", "2h")),
        ("/today", ("hoy", "")),
        ("/hours btc", ("horas", "btc")),
        ("/weekday btc", ("diasemana", "btc")),
        ("/breakeven", ("equilibrio", "")),
        ("/inventado", ("inventado", "")),  # se decide luego que no existe
    ],
)
def test_interpretar(texto, esperado):
    assert interpretar(texto) == esperado


@pytest.mark.parametrize(
    "texto", ["", "   ", "hola", "status", "precio /status", "btc hola", "btc " * 11]
)
def test_lo_que_no_es_comando(texto):
    assert interpretar(texto) is None


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("btc", ("precio", "btc")),
        ("  BTC ", ("precio", "BTC")),
        ("bitcoin", ("precio", "bitcoin")),
        ("btc eth, sol", ("precio", "btc eth, sol")),
    ],
)
def test_criptos_a_secas_son_precio(texto, esperado):
    assert interpretar(texto) == esperado


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


def test_ayuda_a_secas_es_la_lista():
    assert ayuda() == AYUDA
    assert "/ayuda alerta" in AYUDA


@pytest.mark.parametrize("pedido", ["alerta", "/alerta", "ALERTA", "alert"])
def test_ayuda_de_un_comando(pedido):
    texto = ayuda(pedido)

    assert texto.startswith("<b>/alerta</b> — ")
    assert "<code>/alerta bitcoin +10%</code>" in texto


def test_ayuda_de_uno_sin_ejemplos_da_su_linea():
    assert ayuda("miedo") == f"<b>/miedo</b> — {COMANDOS['miedo']}"


def test_ayuda_de_uno_mal_escrito_sugiere():
    assert ayuda("alertaa").endswith("¿Querías decir /ayuda alerta?")
    assert ayuda("histroy").endswith("¿Querías decir /ayuda historico?")


def test_ayuda_de_uno_que_no_existe():
    assert (
        ayuda("<b>bailar") == "No conozco /&lt;b&gt;bailar. Con /ayuda te salen todos."
    )


def test_los_ejemplos_son_de_comandos_que_existen():
    assert set(EJEMPLOS) <= set(COMANDOS)
    for nombre, ejemplos in EJEMPLOS.items():
        for ejemplo, _ in ejemplos:
            orden = interpretar(ejemplo)
            assert orden and orden[0] in (nombre, "precio")
