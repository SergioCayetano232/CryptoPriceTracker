"""/ratio: cuánto vale una cripto en otra y cómo ha cambiado."""

from dataclasses import dataclass
from datetime import date

from .periodo import PeriodoError, es_tramo, leer
from .simbolos import a_id

POR_DEFECTO = 30 * 24

EJEMPLO = "/ratio eth btc 30d"


@dataclass(frozen=True)
class Ratio:
    dias: list[tuple[date, float]]  # lo que vale una en la otra, día a día

    @property
    def ahora(self) -> float:
        return self.dias[-1][1]

    @property
    def antes(self) -> float:
        return self.dias[0][1]

    @property
    def desde(self) -> date:
        return self.dias[0][0]

    @property
    def cambio(self) -> float:
        return (self.ahora / self.antes - 1) * 100

    @property
    def maximo(self) -> float:
        return max(v for _, v in self.dias)

    @property
    def minimo(self) -> float:
        return min(v for _, v in self.dias)

    @property
    def posicion(self) -> float | None:
        """Como en /rango: 0 en el mínimo, 100 en el máximo."""
        if self.maximo == self.minimo:
            return None
        return (self.ahora - self.minimo) / (self.maximo - self.minimo) * 100


def interpretar(argumento: str) -> tuple[list[str], float]:
    """'eth btc 7d' -> (['ethereum', 'bitcoin'], 168). Sin criptos, []."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if len(partes) not in (0, 2):
        raise PeriodoError(f"De dos en dos. Escríbelo así: {EJEMPLO}")
    ids = [a_id(p) for p in partes]
    if ids and ids[0] == ids[1]:
        raise PeriodoError("Son la misma cripto: siempre vale 1")
    return ids, horas


def calcular(
    una: list[tuple[date, float]], otra: list[tuple[date, float]]
) -> Ratio | None:
    """Con el cierre de cada día de las dos. None si no coinciden dos días."""
    precios = dict(otra)
    dias = [(d, p / precios[d]) for d, p in una if precios.get(d)]
    if len(dias) < 2:
        return None
    return Ratio(dias)
