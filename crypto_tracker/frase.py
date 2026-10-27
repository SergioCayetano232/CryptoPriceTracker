"""/frase: una frase famosa del mundo cripto, al azar."""

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Frase:
    texto: str
    autor: str
    año: int | None = None


# Traducidas, menos las que solo tienen gracia tal cual las escribieron.
FRASES = (
    Frase(
        "Si no te lo crees o no lo entiendes, no tengo tiempo de intentar "
        "convencerte, lo siento.",
        "Satoshi Nakamoto",
        2010,
    ),
    Frase(
        "Puede que tenga sentido hacerse con unos pocos, por si acaso cuaja.",
        "Satoshi Nakamoto",
        2009,
    ),
    Frase(
        "Las monedas perdidas solo hacen que las de los demás valgan un poco "
        "más. Piensa en ello como una donación a todos.",
        "Satoshi Nakamoto",
        2010,
    ),
    Frase(
        "El problema de fondo del dinero de siempre es toda la confianza que "
        "hace falta para que funcione.",
        "Satoshi Nakamoto",
        2009,
    ),
    Frase(
        "Estoy seguro de que dentro de 20 años habrá o muchísimo volumen o ninguno.",
        "Satoshi Nakamoto",
        2010,
    ),
    Frase("Running bitcoin", "Hal Finney", 2009),
    Frase("I AM HODLING", "GameKyuubi", 2013),
    Frase("Bitcoin es una proeza tecnológica.", "Bill Gates", 2014),
    Frase(
        "Bitcoin es probablemente veneno para ratas al cuadrado.",
        "Warren Buffett",
        2018,
    ),
    Frase("Si no son tus claves, no son tus monedas.", "Andreas Antonopoulos"),
)


def elegir(azar: random.Random | None = None) -> Frase:
    return (azar or random).choice(FRASES)
