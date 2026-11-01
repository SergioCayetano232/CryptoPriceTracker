"""/sofa: cuántos sofás te da tu cartera."""

import math
from dataclasses import dataclass

# Uno de tres plazas de IKEA, de los de tela. Los de piel se van al doble.
PRECIO = 500


@dataclass(frozen=True)
class Sofa:
    valor: float  # lo que vale tu cartera

    @property
    def enteros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def parte(self) -> float:
        """% de un sofá, para cuando no llega a uno."""
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        return (self.enteros + 1) * PRECIO - self.valor
