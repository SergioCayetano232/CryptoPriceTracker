"""/apy: cuánta cripto tendrías dejándola en staking a un % al año."""

import re
from dataclasses import dataclass

from .puntuales import numero
from .simbolos import a_id

EJEMPLO = "/apy eth 4%"

# Sin decir cuántos años, estos. Más de 50 ya no es un plan de nadie.
AÑOS = (1, 3, 5, 10)
MAX_AÑOS = 50

_AÑOS = re.compile(r"(\d+)(a|años?)")


class ApyError(Exception):
    """Lo que escribiste en /apy no se entiende."""


@dataclass(frozen=True)
class Peticion:
    coin_id: str
    apy: float  # en %
    cantidad: float | None = None  # sin ella, la que tienes en la cartera
    años: int | None = None


@dataclass(frozen=True)
class Tramo:
    años: int
    cantidad: float  # la que tendrías entonces
    ganado: float  # lo que ha puesto el staking, en cripto


def interpretar(argumento: str) -> Peticion:
    """'eth 4%', '2 eth 4%' o 'eth 4% 5a'. El orden de cada cosa da igual."""
    # '5 años' con espacio: si no, el 5 parecería la cantidad.
    texto = re.sub(r"(\d+)\s+(años?)\b", r"\1\2", argumento.lower())
    partes = [p for p in texto.split() if p not in {"al", "año"}]
    coin_id = cantidad = apy = años = None
    for parte in partes:
        if parte.endswith("%"):
            apy = numero(parte[:-1])
            if apy is None or not 0 < apy <= 1000:
                raise ApyError(f"'{parte}' no es un interés. Ej: {EJEMPLO}")
        elif m := _AÑOS.fullmatch(parte):
            años = int(m.group(1))
            if not 1 <= años <= MAX_AÑOS:
                raise ApyError(f"De 1 a {MAX_AÑOS} años. Ej: /apy eth 4% 5a")
        elif (valor := numero(parte)) is not None:
            if valor <= 0:
                raise ApyError(f"'{parte}' no es una cantidad. Ej: /apy 2 eth 4%")
            cantidad = valor
        elif coin_id is None:
            coin_id = a_id(parte)
        else:
            raise ApyError(f"No entiendo '{parte}'. Ej: {EJEMPLO}")

    if coin_id is None or apy is None:
        raise ApyError(
            f"Escríbelo así: {EJEMPLO} (la cripto y lo que da al año). "
            "Con cuánta, /apy 2 eth 4%; con los años, /apy eth 4% 5a"
        )
    return Peticion(coin_id, apy, cantidad, años)


def calcular(cantidad: float, apy: float, años: int | None = None) -> list[Tramo]:
    # El APY ya lleva dentro el compuesto de lo que paga cada pocos días: va tal cual.
    tramos = []
    for n in (años,) if años else AÑOS:
        final = cantidad * (1 + apy / 100) ** n
        tramos.append(Tramo(n, final, final - cantidad))
    return tramos
