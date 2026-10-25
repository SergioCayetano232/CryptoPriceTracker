"""/halving: cuánto falta para que se reduzca a la mitad lo que se paga por bloque."""

from dataclasses import dataclass
from datetime import date, timedelta

# El último que pasó de verdad, en el bloque 840.000.
ULTIMO = date(2024, 4, 20)
RECOMPENSA = 3.125
# 210.000 bloques a 10 minutos. En la práctica salen algo más rápidos, así que
# la fecha es una estimación y puede adelantarse unas semanas.
CICLO = timedelta(minutes=210_000 * 10)


@dataclass(frozen=True)
class Halving:
    anterior: date
    siguiente: date
    recompensa: float  # la de ahora; después del halving, la mitad
    hoy: date

    @property
    def faltan(self) -> int:
        return (self.siguiente - self.hoy).days

    @property
    def hecho(self) -> float:
        """% del ciclo que ya ha pasado."""
        total = (self.siguiente - self.anterior).days
        return (self.hoy - self.anterior).days / total * 100


def calcular(hoy: date) -> Halving:
    anterior, recompensa = ULTIMO, RECOMPENSA
    # Por si el bot sigue funcionando en 2028: salta al ciclo que toque.
    while (siguiente := (anterior + CICLO)) <= hoy:
        anterior, recompensa = siguiente, recompensa / 2
    return Halving(anterior, siguiente, recompensa, hoy)
