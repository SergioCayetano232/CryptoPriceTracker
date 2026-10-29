"""/cana: cuántas cañas te da tu cartera."""

import math
from dataclasses import dataclass

# Una caña en un bar normal. En Madrid centro sale más cara, en un pueblo menos.
PRECIO = 3
AMIGOS = 4


@dataclass(frozen=True)
class Cana:
    valor: float  # lo que vale tu cartera

    @property
    def cuantas(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def rondas(self) -> int:
        """Invitando tú, siendo cuatro."""
        return self.cuantas // AMIGOS
