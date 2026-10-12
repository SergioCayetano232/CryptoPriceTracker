"""/rango: entre qué precios se ha movido una cripto y dónde está hoy."""

from dataclasses import dataclass
from datetime import datetime

from .periodo import PeriodoError, es_tramo, leer
from .simbolos import a_id

POR_DEFECTO = 7 * 24

EJEMPLO = "/rango bitcoin 7d"


@dataclass(frozen=True)
class Rango:
    maximo: float
    cuando_maximo: datetime
    minimo: float
    cuando_minimo: datetime
    media: float
    ahora: float

    @property
    def posicion(self) -> float | None:
        """En qué punto del rango está, en %: 0 en el mínimo, 100 en el máximo."""
        if self.maximo == self.minimo:
            return None
        return (self.ahora - self.minimo) / (self.maximo - self.minimo) * 100


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 30d' -> ('bitcoin', 720). Sin tramo, 7 días; sin cripto, ''."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if len(partes) > 1:
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")
    return (a_id(partes[0]) if partes else ""), horas


def calcular(serie: list[tuple[datetime, float]]) -> Rango | None:
    """serie va del más viejo al más nuevo. None si no hay ni dos precios."""
    if len(serie) < 2:
        return None
    # Con empate, el más reciente: es el que uno recuerda.
    alto = max(reversed(serie), key=lambda f: f[1])
    bajo = min(reversed(serie), key=lambda f: f[1])
    media = sum(p for _, p in serie) / len(serie)
    return Rango(alto[1], alto[0], bajo[1], bajo[0], media, serie[-1][1])


def barra(posicion: float, ancho: int = 10) -> str:
    """'━━━━━●━━━━': el punto es donde está hoy."""
    punto = round(posicion / 100 * (ancho - 1))
    return "━" * punto + "●" + "━" * (ancho - 1 - punto)
