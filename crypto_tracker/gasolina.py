"""/gasolina: cuántos litros de gasolina te da tu cartera."""

import math
from dataclasses import dataclass

# La 95 en España anda por ahí en otoño de 2026. Como el café, no es una cuenta seria.
PRECIO = 1.8

# Un depósito de un coche normal.
DEPOSITO = 50


@dataclass(frozen=True)
class Gasolina:
    valor: float  # lo que vale tu cartera

    @property
    def litros(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def depositos(self) -> int:
        return self.litros // DEPOSITO
