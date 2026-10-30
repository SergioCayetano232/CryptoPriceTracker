"""/metro: cuántos meses de abono de transporte te paga tu cartera."""

import math
from dataclasses import dataclass

# Abono mensual de ciudad grande ya con descuento. Cambia mucho de una a otra.
PRECIO = 30


@dataclass(frozen=True)
class Metro:
    valor: float  # lo que vale tu cartera

    @property
    def meses(self) -> int:
        return math.floor(self.valor / PRECIO)
