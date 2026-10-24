"""/sube: cuánto ha subido desde el mínimo y la mejor subida del tramo."""

from dataclasses import dataclass
from datetime import datetime

from .periodo import PeriodoError, es_tramo, leer
from .simbolos import a_id

POR_DEFECTO = 30 * 24

EJEMPLO = "/sube bitcoin 30d"


@dataclass(frozen=True)
class Subida:
    minimo: float
    cuando_minimo: datetime
    ahora: float
    # La mejor subida de un valle a un pico posterior, aunque luego cayera.
    valle: float
    cuando_valle: datetime
    pico: float
    cuando_pico: datetime

    @property
    def desde_minimo(self) -> float:
        return (self.ahora / self.minimo - 1) * 100

    @property
    def para_volver(self) -> float:
        # Al revés que en /caida: tras un +40%, volver al mínimo es un -28,57%.
        return (self.minimo / self.ahora - 1) * 100

    @property
    def mejor(self) -> float:
        return (self.pico / self.valle - 1) * 100


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 7d' -> ('bitcoin', 168). Sin tramo, 30 días; sin cripto, ''."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if len(partes) > 1:
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")
    return (a_id(partes[0]) if partes else ""), horas


def calcular(serie: list[tuple[datetime, float]]) -> Subida | None:
    """serie va del más viejo al más nuevo. None si no hay ni dos precios."""
    if len(serie) < 2:
        return None

    bajo = serie[0]
    valle, pico = serie[0], serie[0]
    for fila in serie[1:]:
        # <= para quedarme con el mínimo más reciente si se repite
        if fila[1] <= bajo[1]:
            bajo = fila
        elif fila[1] / bajo[1] > pico[1] / valle[1]:
            valle, pico = bajo, fila

    return Subida(bajo[1], bajo[0], serie[-1][1], valle[1], valle[0], pico[1], pico[0])
