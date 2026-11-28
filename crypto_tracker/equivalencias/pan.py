"""/pan: cuántas barras de pan te da tu cartera."""

import math
from dataclasses import dataclass

# La barra de toda la vida en la panadería, no la del súper a 50 céntimos.
PRECIO = 1.20


@dataclass(frozen=True)
class Pan:
    valor: float  # lo que vale tu cartera

    @property
    def enteros(self) -> int:
        # Redondeo antes porque con 1,20 a veces 3,60 / 1,20 da 2,9999...
        return math.floor(round(self.valor / PRECIO, 6))

    @property
    def parte(self) -> float:
        """% de una barra, para cuando no llega a una."""
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        return (self.enteros + 1) * PRECIO - self.valor
