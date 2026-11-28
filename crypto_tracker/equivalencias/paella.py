"""/paella: cuántas paellas para cuatro te da tu cartera."""

import math
from dataclasses import dataclass

# En un restaurante de la playa, para cuatro. En casa sale a la cuarta parte.
PRECIO = 60


@dataclass(frozen=True)
class Paella:
    valor: float  # lo que vale tu cartera

    @property
    def enteros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def parte(self) -> float:
        """% de una paella, para cuando no llega a una."""
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        return (self.enteros + 1) * PRECIO - self.valor
