"""/bici: cuántas bicis de carretera te da tu cartera."""

import math
from dataclasses import dataclass

# Una de aluminio para empezar. Las de carbono buenas pasan de 2.000 sin pestañear.
PRECIO = 800


@dataclass(frozen=True)
class Bici:
    valor: float  # lo que vale tu cartera

    @property
    def enteras(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def parte(self) -> float:
        """% de una bici, para cuando no llega a una."""
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        return (self.enteras + 1) * PRECIO - self.valor
