"""/netflix: cuántos meses de Netflix te paga tu cartera."""

import math
from dataclasses import dataclass

# El plan Estándar en España, sin anuncios.
PRECIO = 13.99


@dataclass(frozen=True)
class Netflix:
    valor: float  # lo que vale tu cartera

    @property
    def meses(self) -> int:
        return math.floor(self.valor / PRECIO)
