"""/navidad: los días que faltan para Navidad y tu cartera en cestas."""

import math
from dataclasses import dataclass
from datetime import date

# Una cesta normal de empresa: turrón, embutido, una botella de cava y poco más.
PRECIO = 100


def navidad(hoy: date) -> date:
    este = date(hoy.year, 12, 25)
    return este if hoy <= este else date(hoy.year + 1, 12, 25)


@dataclass(frozen=True)
class Navidad:
    valor: float  # lo que vale tu cartera
    hoy: date

    @property
    def cestas(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def faltan(self) -> int:
        return (navidad(self.hoy) - self.hoy).days
