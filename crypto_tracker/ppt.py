"""/ppt: piedra, papel o tijera contra el bot, y el que gane decide."""

import random

EJEMPLO = "/ppt piedra"

EMOJIS = {"piedra": "✊", "papel": "✋", "tijera": "✌️"}

# Lo que gana a cada una.
LE_GANA = {"piedra": "papel", "papel": "tijera", "tijera": "piedra"}

# Con tijeras y los emojis también, que es como lo escribe la gente.
NOMBRES = {
    "piedra": "piedra",
    "papel": "papel",
    "tijera": "tijera",
    "tijeras": "tijera",
    "✊": "piedra",
    "✋": "papel",
    "✌️": "tijera",
    "✌": "tijera",
}

QUE_HACER = {
    "ganas": "Ganas tú: compra, que hoy tienes la suerte de cara",
    "pierdes": "Gana el bot: hoy ni la toques",
    "empate": "Empate: ni compres ni vendas, HODL",
}


class PptError(Exception):
    """Lo que has sacado no es piedra, papel ni tijera."""


def interpretar(argumento: str) -> str:
    partes = argumento.lower().split()
    if len(partes) != 1 or partes[0] not in NOMBRES:
        raise PptError(f"Saca piedra, papel o tijera. Ej: {EJEMPLO}")
    return NOMBRES[partes[0]]


def sacar(azar: random.Random | None = None) -> str:
    return (azar or random).choice(list(EMOJIS))


def resultado(tuya: str, del_bot: str) -> str:
    if tuya == del_bot:
        return "empate"
    return "pierdes" if LE_GANA[tuya] == del_bot else "ganas"
