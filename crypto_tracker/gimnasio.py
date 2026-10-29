"""/gimnasio: cuántos meses de gimnasio te paga tu cartera."""

import math
from dataclasses import dataclass

# Un gimnasio de barrio. Los low cost andan por 25 y los buenos pasan de 60.
PRECIO = 40


@dataclass(frozen=True)
class Gimnasio:
    valor: float  # lo que vale tu cartera

    @property
    def meses(self) -> int:
        return math.floor(self.valor / PRECIO)
