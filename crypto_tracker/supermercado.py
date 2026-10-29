"""/super: cuántos carros de la compra te da tu cartera."""

import math
from dataclasses import dataclass

# La compra de la semana para dos, más o menos.
PRECIO = 100


@dataclass(frozen=True)
class Super:
    valor: float  # lo que vale tu cartera

    @property
    def carros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def años(self) -> float:
        return self.carros / 52
