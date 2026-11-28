"""/ideal: el reparto que quieres, y el aviso de cuando la cartera se aleja de él."""

import json
from dataclasses import dataclass

from . import rebalanceo
from .avisos.puntuales import numero
from .cartera import Valor

EJEMPLO = "/ideal btc 60 eth 40"

# Puntos de diferencia a los que avisa si no dices otra cosa.
MARGEN = 5
MARGEN_MAXIMO = 50

# Para volver a avisar tiene que haberse arreglado hasta la mitad del margen.
# Si no, una rondando el límite daría un aviso cada vez que lo cruza.
VUELTA = 0.5

_QUITAR = frozenset({"no", "off", "quitar", "quita", "fuera"})
QUITAR = "quitar"


class IdealError(Exception):
    """El reparto no se entiende."""


@dataclass(frozen=True)
class Ideal:
    reparto: dict[str, float]
    margen: float = MARGEN


@dataclass(frozen=True)
class Parte:
    coin_id: str
    peso: float  # el % que es ahora
    objetivo: float  # el % que quieres

    @property
    def puntos(self) -> float:
        """Lo que le sobra (+) o le falta (-), en puntos."""
        return self.peso - self.objetivo


def interpretar(argumento: str) -> Ideal | str | None:
    """None es enseñar el que hay; QUITAR, quitarlo; si no, el nuevo.

    'btc 60 eth 40' o 'btc 60 eth 40 margen 10'.
    """
    palabras = argumento.split()
    if not palabras:
        return None
    if len(palabras) == 1 and palabras[0].lower() in _QUITAR:
        return QUITAR

    margen = float(MARGEN)
    if len(palabras) >= 2 and palabras[-2].lower() == "margen":
        leido = numero(palabras[-1].rstrip("%"))
        if leido is None or not 1 <= leido <= MARGEN_MAXIMO:
            raise IdealError(
                f"El margen va de 1 a {MARGEN_MAXIMO} puntos. Así: {EJEMPLO} margen 10"
            )
        margen = leido
        palabras = palabras[:-2]

    try:
        reparto = rebalanceo.interpretar(" ".join(palabras))
    except rebalanceo.RebalanceoError as e:
        raise IdealError(str(e).replace(rebalanceo.EJEMPLO, EJEMPLO)) from None
    if not reparto:
        raise IdealError(f"Falta el reparto. Así: {EJEMPLO}")
    return Ideal(reparto, margen)


def a_texto(ideal: Ideal) -> str:
    return json.dumps({"reparto": ideal.reparto, "margen": ideal.margen})


def de_texto(texto: str | None) -> Ideal | None:
    """Lo guardado. None si no hay nada o no se entiende."""
    if not texto:
        return None
    try:
        datos = json.loads(texto)
        reparto = {str(c): float(p) for c, p in datos["reparto"].items()}
        return Ideal(reparto, float(datos["margen"])) if reparto else None
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


def partes(valores: list[Valor], reparto: dict[str, float]) -> list[Parte]:
    """Cada cripto con lo que pesa y lo que querías, la más alejada primero.

    Las que tienes y no están en el reparto cuentan como que las quieres a 0.
    """
    total = sum(v.valor for v in valores)
    if total <= 0:
        return []
    tienes = {v.coin_id: v.valor for v in valores}
    lista = [
        Parte(c, tienes.get(c, 0.0) / total * 100, reparto.get(c, 0.0))
        for c in dict.fromkeys([*reparto, *tienes])
    ]
    return sorted(lista, key=lambda p: -abs(p.puntos))


def fuera(lista: list[Parte], margen: float) -> list[Parte]:
    return [p for p in lista if abs(p.puntos) >= margen]


def toca(lista: list[Parte], margen: float, avisado: bool) -> bool:
    return not avisado and bool(fuera(lista, margen))


def sigue_avisado(lista: list[Parte], margen: float, avisado: bool) -> bool:
    """Si no toca avisar, si se queda apuntado que ya se avisó."""
    return avisado and bool(fuera(lista, margen * VUELTA))


def comando(reparto: dict[str, float]) -> str:
    """El /rebalanceo que te devuelve a ese reparto, para copiar."""
    trozos = (f"{c} {p:g}" for c, p in reparto.items())
    return "/rebalanceo " + " ".join(trozos)
