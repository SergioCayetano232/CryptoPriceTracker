"""/caraocruz: compro o vendo, decidido con una moneda al aire."""

import random

from .simbolos import a_id

QUE_HACER = {"cara": "compra", "cruz": "vende"}


def lanzar(azar: random.Random | None = None) -> str:
    return (azar or random).choice(list(QUE_HACER))


def interpretar(argumento: str) -> str | None:
    """La cripto, si la dices. Solo una: con más no sabría a cuál le toca."""
    partes = argumento.split()
    return a_id(partes[0]) if len(partes) == 1 else None
