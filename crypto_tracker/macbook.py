"""/macbook: cuántos MacBook Air te da tu cartera."""

import math
from dataclasses import dataclass

# El Air de 13" con 16 GB, el que se compra casi todo el mundo. Sale a unos 1.200.
PRECIO = 1_300


@dataclass(frozen=True)
class Macbook:
    valor: float  # lo que vale tu cartera

    @property
    def enteros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def parte(self) -> float:
        """% de un MacBook, para cuando no llega a uno."""
        return self.valor / PRECIO * 100

    @property
    def falta(self) -> float:
        return (self.enteros + 1) * PRECIO - self.valor
