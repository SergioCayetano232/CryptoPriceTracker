"""/libro: cuántos libros te da tu cartera."""

import math
from dataclasses import dataclass

# Una novela nueva en tapa blanda. De bolsillo salen a la mitad.
PRECIO = 20


@dataclass(frozen=True)
class Libro:
    valor: float  # lo que vale tu cartera

    @property
    def libros(self) -> int:
        return math.floor(self.valor / PRECIO)
