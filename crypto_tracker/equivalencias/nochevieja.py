"""/nochevieja: lo que queda de año y tu cartera en botellas de cava."""

import math
from dataclasses import dataclass
from datetime import date

# Un cava normal de supermercado, ni el más barato ni de los de regalo.
PRECIO = 10


@dataclass(frozen=True)
class Nochevieja:
    valor: float  # lo que vale tu cartera
    hoy: date

    @property
    def faltan(self) -> int:
        # El 31 siempre es de este año, así que nunca sale negativo.
        return (date(self.hoy.year, 12, 31) - self.hoy).days

    @property
    def pasado(self) -> float:
        """% del año que ya se ha ido. Cuenta los bisiestos."""
        inicio = date(self.hoy.year, 1, 1)
        dias = (date(self.hoy.year + 1, 1, 1) - inicio).days
        return (self.hoy - inicio).days / dias * 100

    @property
    def botellas(self) -> int:
        return math.floor(self.valor / PRECIO)
