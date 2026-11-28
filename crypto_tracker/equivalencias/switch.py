"""/switch: cuántas Switch 2 te da tu cartera."""

import math
from dataclasses import dataclass

# Salió a 469,99 € sin juego. Redondeo.
PRECIO = 470


@dataclass(frozen=True)
class Switch:
    valor: float  # lo que vale tu cartera

    @property
    def enteros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def parte(self) -> float:
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        return (self.enteros + 1) * PRECIO - self.valor
