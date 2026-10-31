"""/churros: cuántos chocolates con churros te da tu cartera."""

import math
from dataclasses import dataclass

# Una taza y media docena en una churrería normal. En San Ginés ya es otra cosa.
PRECIO = 4


@dataclass(frozen=True)
class Churros:
    valor: float  # lo que vale tu cartera

    @property
    def raciones(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def años(self) -> float:
        """Desayunando unos cada domingo."""
        return self.raciones / 52
