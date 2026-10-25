"""/redondo: cuánto le falta a una cripto para la siguiente cifra redonda."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Redondo:
    ahora: float
    arriba: float
    abajo: float

    @property
    def falta_arriba(self) -> float:
        return (self.arriba / self.ahora - 1) * 100

    @property
    def falta_abajo(self) -> float:
        return (self.abajo / self.ahora - 1) * 100


def escalon(precio: float) -> float:
    """De cuánto en cuánto van las cifras redondas a ese precio."""
    paso = 10 ** math.floor(math.log10(precio))
    # Con 10.500 el siguiente "redondo" sería 20.000, demasiado lejos.
    if precio / paso < 2:
        paso /= 10
    return paso


def calcular(precio: float) -> Redondo:
    paso = escalon(precio)
    # El round quita los restos de coma flotante: 0.30000000000000004 y cosas así.
    abajo = round(math.floor(precio / paso) * paso, 12)
    if abajo >= precio:
        abajo = round(abajo - paso, 12)
    arriba = round(abajo + paso, 12)
    if arriba <= precio:
        arriba = round(arriba + paso, 12)
    return Redondo(precio, arriba, abajo)
