"""/menu: cuántos menús del día te da tu cartera."""

import math
from dataclasses import dataclass

# Primero, segundo, postre y bebida en un bar normal. En Madrid ya pasa de 13.
PRECIO = 13


@dataclass(frozen=True)
class Menu:
    valor: float  # lo que vale tu cartera

    @property
    def menus(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def semanas(self) -> int:
        """Comiendo fuera de lunes a viernes."""
        return self.menus // 5

    @property
    def años(self) -> float:
        return self.semanas / 52
