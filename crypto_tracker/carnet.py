"""/carnet: cuántos carnets de conducir te da tu cartera."""

import math
from dataclasses import dataclass

# El B en autoescuela, con unas veinte prácticas y las tasas de Tráfico.
# Si suspendes el práctico, súmale otro tanto.
PRECIO = 800


@dataclass(frozen=True)
class Carnet:
    valor: float  # lo que vale tu cartera

    @property
    def enteros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def parte(self) -> float:
        """% de un carnet, para cuando no llega a uno."""
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        return (self.enteros + 1) * PRECIO - self.valor
