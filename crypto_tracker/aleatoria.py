"""/aleatoria: una de las más grandes al azar, para descubrir alguna nueva."""

import random

from .top import Movida

# Las estables valen siempre 1 y no hay nada que descubrir. Casi todas llevan
# USD en el símbolo (USDT, USDC, FDUSD...); estas son las que no.
ESTABLES = {"DAI", "EURC", "EURS", "GHO", "FRAX", "BUIDL", "U"}


def es_estable(m: Movida) -> bool:
    return "USD" in m.simbolo or m.simbolo in ESTABLES


def elegir(
    lista: list[Movida], vigiladas: set[str], azar: random.Random | None = None
) -> tuple[int, Movida] | None:
    """(puesto, cripto). lista viene de mayor a menor. Las que ya vigilas no salen."""
    candidatas = [
        (puesto, m)
        for puesto, m in enumerate(lista, 1)
        if m.coin_id not in vigiladas and not es_estable(m)
    ]
    if not candidatas:
        return None
    return (azar or random).choice(candidatas)
