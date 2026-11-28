"""/vuelo: cuántos viajes a Nueva York te da tu cartera."""

import math
from dataclasses import dataclass

# Ida y vuelta desde Madrid en turista, cogido con algo de tiempo. En agosto, más.
PRECIO = 600


@dataclass(frozen=True)
class Vuelo:
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
