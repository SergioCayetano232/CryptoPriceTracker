"""/iphone: cuántos iPhone te da tu cartera."""

import math
from dataclasses import dataclass

# El 18 Pro de 256 GB salió a 1.469 € en España. Redondeo, como con el Lamborghini.
PRECIO = 1_500


@dataclass(frozen=True)
class Iphone:
    valor: float  # lo que vale tu cartera

    @property
    def enteros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def parte(self) -> float:
        """% de un iPhone, para cuando no llega a uno."""
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        return (self.enteros + 1) * PRECIO - self.valor
