"""/futbol: cuántas entradas de fútbol te da tu cartera."""

import math
from dataclasses import dataclass

# Un partido de liga normal, en grada lateral. Contra el Madrid o el Barça, el doble.
PRECIO = 60
# 38 jornadas, la mitad en casa.
EN_CASA = 19


@dataclass(frozen=True)
class Futbol:
    valor: float  # lo que vale tu cartera

    @property
    def entradas(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def temporadas(self) -> float:
        """Yendo a todos los partidos en casa."""
        return self.entradas / EN_CASA
