"""/fibonacci: dónde podría frenar una subida o una bajada."""

from dataclasses import dataclass
from datetime import datetime

from .periodo import PeriodoError, es_tramo, leer
from .rango import Rango
from .rango import calcular as calcular_rango
from .simbolos import a_id

POR_DEFECTO = 90 * 24
EJEMPLO = "/fibonacci bitcoin 90d"

# El 61,8% es el que más se mira; el 50% no es de Fibonacci pero lo pone todo el mundo.
NIVELES = [0.0, 23.6, 38.2, 50.0, 61.8, 78.6, 100.0]

# Por debajo, el máximo y el mínimo están tan cerca que los niveles se pisan.
MIN_AMPLITUD = 1.0


@dataclass(frozen=True)
class Nivel:
    pct: float
    precio: float


@dataclass(frozen=True)
class Fibonacci:
    rango: Rango
    subiendo: bool  # el mínimo vino antes que el máximo
    niveles: list[Nivel]  # de precio más alto a más bajo

    @property
    def ahora(self) -> float:
        return self.rango.ahora

    @property
    def debajo(self) -> Nivel | None:
        """El primero por debajo del precio de ahora."""
        return next((n for n in self.niveles if n.precio < self.ahora), None)

    @property
    def encima(self) -> Nivel | None:
        return next((n for n in reversed(self.niveles) if n.precio > self.ahora), None)


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 30d' -> ('bitcoin', 720). Sin tramo, 90 días; sin cripto, ''."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if len(partes) > 1:
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")
    return (a_id(partes[0]) if partes else ""), horas


def calcular(serie: list[tuple[datetime, float]]) -> Fibonacci | None:
    """None si no hay precios o apenas se ha movido."""
    r = calcular_rango(serie)
    if r is None or r.minimo <= 0 or r.amplitud < MIN_AMPLITUD:
        return None

    subiendo = r.cuando_minimo < r.cuando_maximo
    tramo = r.maximo - r.minimo
    # Subiendo, se cuenta desde el máximo hacia abajo: lo que podría corregir.
    # Bajando, desde el mínimo hacia arriba: hasta dónde podría rebotar.
    if subiendo:
        niveles = [Nivel(p, r.maximo - tramo * p / 100) for p in NIVELES]
    else:
        niveles = [Nivel(p, r.minimo + tramo * p / 100) for p in reversed(NIVELES)]
    return Fibonacci(r, subiendo, niveles)
