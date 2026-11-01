"""/videojuego: cuántos juegos nuevos te da tu cartera."""

import math
from dataclasses import dataclass

# Lo que cuesta ya un lanzamiento grande de PS5 o Switch 2 el primer día.
PRECIO = 80


@dataclass(frozen=True)
class Videojuego:
    valor: float  # lo que vale tu cartera

    @property
    def juegos(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def años(self) -> float:
        """Comprando uno al mes."""
        return self.juegos / 12
