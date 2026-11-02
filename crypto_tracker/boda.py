"""/boda: cuántas bodas te da tu cartera."""

import math
from dataclasses import dataclass

# La media en España, con banquete para unos cien invitados. Sin viaje de novios.
PRECIO = 25_000


@dataclass(frozen=True)
class Boda:
    valor: float  # lo que vale tu cartera

    @property
    def enteros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def parte(self) -> float:
        """% de una boda, para cuando no llega a una."""
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        return (self.enteros + 1) * PRECIO - self.valor
