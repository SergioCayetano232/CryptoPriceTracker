"""Con qué ánimo compras y vendes, y qué te sale de cada uno: /emocion y /emociones."""

import unicodedata
from dataclasses import dataclass

from .movimientos import Movimiento

# El orden es el de los botones: de lo más frío a lo más caliente.
EMOCIONES = {
    "tranquilo": ("😐", "Tranquilo"),
    "aburrido": ("🥱", "Aburrido"),
    "miedo": ("😱", "Miedo"),
    "fomo": ("😰", "FOMO"),
    "euforia": ("🤩", "Euforia"),
}
# Lo que uno escribe a mano en vez de la palabra del botón.
OTRAS = {
    "tranquila": "tranquilo",
    "calma": "tranquilo",
    "aburrida": "aburrido",
    "aburrimiento": "aburrido",
    "panico": "miedo",
    "eufórico": "euforia",
    "euforico": "euforia",
    "eufórica": "euforia",
    "euforica": "euforia",
}
EJEMPLO = "/emocion 12 miedo"
# Con una sola, decir "con miedo te va mejor" es pasarse.
MINIMO = 2


class EmocionError(Exception):
    """Lo que escribiste en /emocion no se entiende."""


@dataclass(frozen=True)
class Grupo:
    emocion: str
    veces: int
    # En compras, lo que van hoy; en ventas, lo que valdría hoy lo vendido.
    cambio: float | None


@dataclass(frozen=True)
class Emociones:
    compras: list[Grupo]
    ventas: list[Grupo]
    sin: int  # movimientos sin ánimo apuntado

    def mejor_y_peor(self) -> tuple[Grupo, Grupo] | None:
        """La emoción con la que mejor compras y la peor, si se puede decir."""
        con = [g for g in self.compras if g.cambio is not None and g.veces >= MINIMO]
        if len(con) < 2:
            return None
        con.sort(key=lambda g: g.cambio)
        return con[-1], con[0]


def en_frase(emocion: str) -> str:
    """'miedo', 'euforia'... y 'FOMO', que es una sigla."""
    nombre = EMOCIONES[emocion][1]
    return nombre if nombre.isupper() else nombre.lower()


def leer(texto: str) -> str | None:
    """'Eufórico' -> 'euforia'. None si no es ninguna."""
    sin_tildes = "".join(
        c
        for c in unicodedata.normalize("NFD", texto.strip().lower())
        if unicodedata.category(c) != "Mn"
    )
    if sin_tildes in EMOCIONES:
        return sin_tildes
    return OTRAS.get(texto.strip().lower()) or OTRAS.get(sin_tildes)


def interpretar(argumento: str) -> tuple[int, str]:
    """'12 miedo' -> (12, 'miedo')."""
    partes = argumento.replace("#", "").split()
    if len(partes) != 2 or not partes[0].isdigit():
        raise EmocionError(f"Escríbelo así: {EJEMPLO} (el número sale en /movimientos)")
    emocion = leer(partes[1])
    if emocion is None:
        nombres = ", ".join(EMOCIONES)
        raise EmocionError(f"No conozco '{partes[1]}'. Puedes usar: {nombres}")
    return int(partes[0]), emocion


def calcular(movimientos: list[Movimiento], precios: dict[str, float]) -> Emociones:
    compras, ventas, sin = {}, {}, 0
    for m in movimientos:
        if not m.emocion:
            sin += 1
            continue
        lado = compras if m.tipo == "compra" else ventas
        lado.setdefault(m.emocion, []).append(m)
    return Emociones(_grupos(compras, precios), _grupos(ventas, precios), sin)


def _grupos(por: dict[str, list[Movimiento]], precios: dict[str, float]) -> list[Grupo]:
    return [
        Grupo(e, len(por[e]), _cambio(por[e], precios)) for e in EMOCIONES if e in por
    ]


def _cambio(lista: list[Movimiento], precios: dict[str, float]) -> float | None:
    """Lo que vale hoy todo junto contra lo que se pagó o se cobró."""
    validas = [m for m in lista if m.coste and m.coin_id in precios]
    if not validas:
        return None
    dinero = sum(m.coste for m in validas)
    hoy = sum(m.cantidad * precios[m.coin_id] for m in validas)
    return (hoy / dinero - 1) * 100
