"""/cuando: la última vez que una cripto estuvo a un precio."""

from dataclasses import dataclass
from datetime import datetime

from .periodo import MAXIMO
from .puntuales import numero
from .simbolos import a_id

EJEMPLO = "/cuando bitcoin 60000"

# Todo lo guardado: lo que no esté aquí ya lo ha borrado HISTORY_DAYS.
HORAS = MAXIMO


class CuandoError(Exception):
    """Lo que escribiste en /cuando no se entiende."""


@dataclass(frozen=True)
class Cuando:
    objetivo: float
    ahora: float
    por_debajo: bool  # True si se busca cuándo estuvo a ese precio o menos
    cuando: datetime | None  # None si no ha llegado en todo lo guardado
    precio: float | None  # lo que valía entonces
    desde: datetime  # el primer precio guardado
    extremo: float  # lo más cerca que ha estado, si no ha llegado

    @property
    def cambio(self) -> float | None:
        if self.precio is None:
            return None
        return (self.ahora / self.precio - 1) * 100

    @property
    def falta(self) -> float:
        """Lo que tiene que moverse desde ahora para llegar, con signo."""
        return (self.objetivo / self.ahora - 1) * 100


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 60000' -> ('bitcoin', 60000.0). Vale 60k y 60.000 €."""
    partes = [p for p in argumento.lower().split() if p not in {"€", "$", "£", "a"}]
    if len(partes) != 2:
        raise CuandoError(f"Escríbelo así: {EJEMPLO}")

    precio = numero(partes[1])
    if precio is None or precio <= 0:
        raise CuandoError(f"'{partes[1]}' no es un precio. Ej: {EJEMPLO}")
    return a_id(partes[0]), precio


def calcular(serie: list[tuple[datetime, float]], objetivo: float) -> Cuando | None:
    """serie va del más viejo al más nuevo. None si está vacía."""
    if not serie:
        return None

    ahora = serie[-1][1]
    # Si ahora está por encima, lo que interesa es cuándo bajó hasta ahí.
    por_debajo = objetivo <= ahora
    for momento, precio in reversed(serie):
        if precio <= objetivo if por_debajo else precio >= objetivo:
            return Cuando(
                objetivo, ahora, por_debajo, momento, precio, serie[0][0], precio
            )

    precios = [p for _, p in serie]
    extremo = min(precios) if por_debajo else max(precios)
    return Cuando(objetivo, ahora, por_debajo, None, None, serie[0][0], extremo)
