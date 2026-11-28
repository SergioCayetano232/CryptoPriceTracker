"""/cafe: cuántos cafés te da tu cartera."""

import math
from dataclasses import dataclass

# Un café de bar, en euros o en dólares. Como el Lamborghini, no es una cuenta seria.
PRECIO = 1.5


@dataclass(frozen=True)
class Cafe:
    valor: float  # lo que vale tu cartera

    @property
    def cuantos(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def años(self) -> float:
        """Para cuánto te da tomando uno al día."""
        return self.cuantos / 365
