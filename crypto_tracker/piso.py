"""/piso: cuántos metros cuadrados de piso en Madrid te da tu cartera."""

import math
from dataclasses import dataclass

# Madrid capital, de media. En Salamanca o Chamberí pasa de 9.000.
PRECIO = 5_500
METROS = 70


@dataclass(frozen=True)
class Piso:
    valor: float  # lo que vale tu cartera

    @property
    def metros(self) -> float:
        return self.valor / PRECIO

    @property
    def pisos(self) -> int:
        return math.floor(self.metros / METROS)

    @property
    def falta(self) -> float:
        """Lo que falta para el primer piso entero."""
        return max(METROS * PRECIO - self.valor, 0)
