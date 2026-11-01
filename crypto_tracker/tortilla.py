"""/tortilla: cuántos pinchos de tortilla te da tu cartera."""

import math
from dataclasses import dataclass

# Un pincho en un bar de barrio. En el centro de Madrid ya sale a 4 o 5.
PRECIO = 3


@dataclass(frozen=True)
class Tortilla:
    valor: float  # lo que vale tu cartera

    @property
    def pinchos(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def años(self) -> float:
        """Uno cada mañana."""
        return self.pinchos / 365
