"""/zapatillas: cuántos pares de zapatillas te da tu cartera."""

import math
from dataclasses import dataclass

# Unas de marca normales, ni de running caras ni de edición limitada.
PRECIO = 120

# Unas nuevas cada temporada
POR_AÑO = 4


@dataclass(frozen=True)
class Zapatillas:
    valor: float  # lo que vale tu cartera

    @property
    def pares(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def años(self) -> int:
        return self.pares // POR_AÑO
