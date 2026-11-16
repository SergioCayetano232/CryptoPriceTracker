"""Tests de las frases sueltas que se pasan a un comando."""

import pytest

from crypto_tracker.comandos import interpretar
from crypto_tracker.lenguaje import entender, normalizar


def test_normalizar():
    assert normalizar("  ¿Cuánto   VALE BTC? ") == "cuanto vale btc"
    assert normalizar("Avísame si baja.") == "avisame si baja"


@pytest.mark.parametrize(
    "frase, sale",
    [
        ("avísame si btc baja de 60000", ("alerta", "btc 60000")),
        ("Avísame cuando bitcoin llegue a 70.000€", ("alerta", "bitcoin 70.000")),
        ("avísame cuando btc baje de 60000", ("alerta", "btc 60000")),
        ("avísame cuando eth suba un 5%", ("alerta", "eth +5%")),
        ("avísame cuando sol caiga un 5%", ("alerta", "sol -5%")),
        ("avisame si eth sube a 4000 euros", ("alerta", "eth 4000")),
        ("dime si sol pasa de 200", ("alerta", "sol 200")),
        ("avísame si btc supera los 100k", ("alerta", "btc 100k")),
        ("avísame si btc baja de 60 mil", ("alerta", "btc 60k")),
        ("avísame si eth sube un 10%", ("alerta", "eth +10%")),
        ("avísame si eth cae un 7,5 %", ("alerta", "eth -7,5%")),
        ("avísame si mi cartera baja de 5000", ("alerta", "cartera 5000")),
        ("avísame si eth llega a un 10%", None),  # ¿subiendo o bajando?
        ("¿cuánto vale btc?", ("precio", "btc")),
        ("a cuánto está el ethereum ahora", ("precio", "ethereum")),
        ("precio de sol", ("precio", "sol")),
        ("cómo va mi cartera", ("cartera", "")),
        ("¿cuánto vale mi cartera?", ("cartera", "")),
        ("como voy hoy", ("cartera", "")),
        ("cállate", ("mute", "")),
        ("cállate 2 horas", ("mute", "2h")),
        ("silencio una hora", ("mute", "1h")),
        ("no me avises durante media hora", ("mute", "30m")),
        ("cállate 20 minutos", ("mute", "20m")),
        ("¿qué sabes hacer?", ("ayuda", "")),
        ("hola", None),
        ("cómprame bitcoin", None),
        ("he comprado 0.01 btc por 600", None),  # lo que apunta, nunca
        ("", None),
    ],
)
def test_entender(frase, sale):
    assert entender(frase) == sale


def test_interpretar_pasa_las_frases():
    assert interpretar("avísame si btc baja de 60000") == ("alerta", "btc 60000")
    # Las criptos a secas siguen yendo a /precio.
    assert interpretar("btc eth") == ("precio", "btc eth")
    assert interpretar("hola") is None
