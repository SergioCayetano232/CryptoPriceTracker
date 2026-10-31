"""/hotel: cuántas noches de hotel te da tu cartera."""

import math
from dataclasses import dataclass

# Habitación doble de tres estrellas fuera de temporada alta.
PRECIO = 100


@dataclass(frozen=True)
class Hotel:
    valor: float  # lo que vale tu cartera

    @property
    def noches(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def findes(self) -> int:
        """De viernes a domingo, dos noches."""
        return self.noches // 2
