"""/ps5: cuántas PS5 te da tu cartera."""

import math
from dataclasses import dataclass

# La Pro salió a 799,99 € y sigue más o menos ahí. Redondeo.
PRECIO = 800


@dataclass(frozen=True)
class Ps5:
    valor: float  # lo que vale tu cartera

    @property
    def enteros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def parte(self) -> float:
        """% de una PS5, para cuando no llega a una."""
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        return (self.enteros + 1) * PRECIO - self.valor
