"""/kebab: cuántos kebabs te da tu cartera."""

import math
from dataclasses import dataclass

# Un döner de los normales, sin menú ni bebida.
PRECIO = 6


@dataclass(frozen=True)
class Kebab:
    valor: float  # lo que vale tu cartera

    @property
    def kebabs(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def años(self) -> float:
        """Cenando uno cada viernes."""
        return self.kebabs / 52
