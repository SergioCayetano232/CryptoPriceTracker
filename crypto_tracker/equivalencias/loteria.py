"""/loteria: tu cartera en décimos de Navidad y lo que falta para el sorteo."""

import math
from dataclasses import dataclass
from datetime import date

PRECIO = 20


def sorteo(hoy: date) -> date:
    # El día 22 cuenta como "es hoy"; a partir del 23 ya toca el del año que viene.
    este = date(hoy.year, 12, 22)
    return este if hoy <= este else date(hoy.year + 1, 12, 22)


@dataclass(frozen=True)
class Loteria:
    valor: float  # lo que vale tu cartera
    hoy: date

    @property
    def decimos(self) -> int:
        return math.floor(self.valor / PRECIO)

    @property
    def faltan(self) -> int:
        return (sorteo(self.hoy) - self.hoy).days
