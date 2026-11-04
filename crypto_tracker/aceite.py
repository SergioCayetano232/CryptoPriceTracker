"""/aceite: cuántos litros de aceite de oliva te da tu cartera."""

import math
from dataclasses import dataclass

# Virgen extra en el súper, garrafa de 5 litros. En 2024 llegó a pasar de 9.
PRECIO = 8


@dataclass(frozen=True)
class Aceite:
    valor: float  # lo que vale tu cartera

    @property
    def enteros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def parte(self) -> float:
        """% de un litro, para cuando no llega a uno."""
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        return (self.enteros + 1) * PRECIO - self.valor
