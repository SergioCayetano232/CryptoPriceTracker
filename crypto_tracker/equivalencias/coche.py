"""/coche: cuántos coches te da tu cartera."""

import math
from dataclasses import dataclass

# Un utilitario nuevo de gasolina, tipo Ibiza o Clio, sin extras. Lo que
# cobran de verdad al salir del concesionario anda por ahí.
PRECIO = 20_000


@dataclass(frozen=True)
class Coche:
    valor: float  # lo que vale tu cartera

    @property
    def enteros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def parte(self) -> float:
        """% de un coche, para cuando no llega a uno."""
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        return (self.enteros + 1) * PRECIO - self.valor
