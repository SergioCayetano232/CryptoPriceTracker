"""/luz: cuántos meses de factura de la luz te paga tu cartera."""

import math
from dataclasses import dataclass

# Un piso normal, a medias entre invierno y verano.
PRECIO = 60


@dataclass(frozen=True)
class Luz:
    valor: float  # lo que vale tu cartera

    @property
    def meses(self) -> int:
        return math.floor(self.valor / PRECIO)
