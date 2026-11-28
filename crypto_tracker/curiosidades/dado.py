"""/dado: qué hacer con tu cripto, a lo que diga un dado."""

import random

CARAS = "⚀⚁⚂⚃⚄⚅"
# Del 1 al 6, de peor a mejor. Dos de seis para no hacer nada, como en la vida.
# Lo segundo es lo que va delante del nombre si dices la cripto.
QUE_HACER = (
    ("vende todo", "tu"),
    ("vende un poco", "de"),
    ("no toques nada", "de"),
    ("no toques nada", "de"),
    ("compra un poco", "de"),
    ("compra más", ""),
)


def tirar(azar: random.Random | None = None) -> int:
    return (azar or random).randint(1, 6)
