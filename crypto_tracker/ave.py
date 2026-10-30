"""/ave: cuántas escapadas en AVE a Barcelona te da tu cartera."""

import math
from dataclasses import dataclass

# Ida y vuelta desde Madrid comprando con tiempo. Con Ouigo e Iryo ha bajado mucho.
PRECIO = 80


@dataclass(frozen=True)
class Ave:
    valor: float  # lo que vale tu cartera

    @property
    def viajes(self) -> int:
        return math.floor(self.valor / PRECIO)
