"""/cine: cuántas entradas de cine te da tu cartera."""

import math
from dataclasses import dataclass

# Una entrada normal, sin día del espectador ni palomitas.
PRECIO = 9


@dataclass(frozen=True)
class Cine:
    valor: float  # lo que vale tu cartera

    @property
    def entradas(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def años(self) -> float:
        """Yendo una vez por semana."""
        return self.entradas / 52
