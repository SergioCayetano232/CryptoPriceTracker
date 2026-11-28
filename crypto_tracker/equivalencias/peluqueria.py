"""/peluqueria: cuántos cortes de pelo te da tu cartera."""

import math
from dataclasses import dataclass

# Corte de caballero en una de barrio. Lavar y peinar va aparte.
PRECIO = 15


@dataclass(frozen=True)
class Peluqueria:
    valor: float  # lo que vale tu cartera

    @property
    def cortes(self) -> int:
        return math.floor(self.valor / PRECIO)
