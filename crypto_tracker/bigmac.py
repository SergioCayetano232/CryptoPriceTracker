"""/bigmac: cuántos Big Mac te da tu cartera."""

import math
from dataclasses import dataclass

# En el restaurante, no a domicilio, que en Uber Eats sale casi un euro más caro.
PRECIO = 5.5


@dataclass(frozen=True)
class BigMac:
    valor: float  # lo que vale tu cartera

    @property
    def cuantos(self) -> int:
        return math.floor(self.valor / PRECIO)
