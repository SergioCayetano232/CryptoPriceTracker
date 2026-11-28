"""/jamon: cuántos jamones ibéricos te da tu cartera."""

import math
from dataclasses import dataclass

# Una pata de bellota 100% ibérica de unos 8 kilos. Los de cebo salen a la mitad.
PRECIO = 500


@dataclass(frozen=True)
class Jamon:
    valor: float  # lo que vale tu cartera

    @property
    def enteros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def parte(self) -> float:
        """% de un jamón, para cuando no llega a uno."""
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        return (self.enteros + 1) * PRECIO - self.valor
