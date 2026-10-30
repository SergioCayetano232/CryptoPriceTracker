"""/concierto: cuántas entradas de concierto te da tu cartera."""

import math
from dataclasses import dataclass

# Sala grande o pabellón, sin gastos de gestión. Un estadio se va al doble.
PRECIO = 50


@dataclass(frozen=True)
class Concierto:
    valor: float  # lo que vale tu cartera

    @property
    def entradas(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def para_dos(self) -> int:
        return self.entradas // 2
