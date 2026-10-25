"""/lambo: cuántos Lamborghinis te da tu cartera."""

import math
from dataclasses import dataclass

# Un Huracán nuevo anda por ahí, en euros o en dólares. No es una cuenta seria.
PRECIO = 250_000


@dataclass(frozen=True)
class Lambo:
    valor: float  # lo que vale tu cartera

    @property
    def enteros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def parte(self) -> float:
        """% de un Lamborghini, para cuando no llega a uno."""
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        """Lo que falta para el siguiente."""
        return (self.enteros + 1) * PRECIO - self.valor
