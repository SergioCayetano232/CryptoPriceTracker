"""/alquiler: cuántos meses de alquiler te paga tu cartera."""

import math
from dataclasses import dataclass

# Un piso de unos 80 m² a lo que va el metro en España este año, redondeado.
PRECIO = 1_100


@dataclass(frozen=True)
class Alquiler:
    valor: float  # lo que vale tu cartera

    @property
    def meses(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def dias(self) -> int:
        """Para cuando no llega a un mes. Cuento meses de 30, sin más lío."""
        return math.floor(self.valor / PRECIO * 30)
