"""/airpods: cuántos AirPods Pro te da tu cartera."""

import math
from dataclasses import dataclass

# Los Pro 3 salieron a 249 €. Redondeo.
PRECIO = 250


@dataclass(frozen=True)
class Airpods:
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
