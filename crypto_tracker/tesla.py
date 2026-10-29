"""/tesla: cuántos Tesla te da tu cartera."""

import math
from dataclasses import dataclass

# El Model 3 básico ronda los 40.000 en España, sin contar ayudas.
PRECIO = 40_000


@dataclass(frozen=True)
class Tesla:
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
