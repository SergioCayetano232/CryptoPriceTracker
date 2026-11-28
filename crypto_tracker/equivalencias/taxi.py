"""/taxi: cuántos taxis al aeropuerto te da tu cartera."""

import math
from dataclasses import dataclass

# La tarifa fija de Madrid entre la M-30 y Barajas, sin propina.
PRECIO = 33


@dataclass(frozen=True)
class Taxi:
    valor: float  # lo que vale tu cartera

    @property
    def viajes(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def escapadas(self) -> int:
        """Ida y vuelta."""
        return self.viajes // 2
