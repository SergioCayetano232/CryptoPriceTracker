"""/croquetas: cuántas raciones de croquetas te da tu cartera."""

import math
from dataclasses import dataclass

# Una ración de ocho caseras en un bar. Las congeladas no cuentan.
PRECIO = 10


@dataclass(frozen=True)
class Croquetas:
    valor: float  # lo que vale tu cartera

    @property
    def enteros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def parte(self) -> float:
        """% de una ración, para cuando no llega a una."""
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        return (self.enteros + 1) * PRECIO - self.valor
