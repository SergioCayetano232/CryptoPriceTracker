"""/doble: a qué precio duplicas lo que metiste en cada cripto."""

from dataclasses import dataclass

from . import equilibrio
from .cartera import Valor


@dataclass(frozen=True)
class Doble:
    coin_id: str
    precio: float  # el de ahora
    medio: float  # a cuánto te salió

    @property
    def objetivo(self) -> float:
        return self.medio * 2

    @property
    def falta(self) -> float:
        """Lo que tiene que subir, en %. Negativo si ya lo has doblado."""
        return (self.objetivo / self.precio - 1) * 100


@dataclass(frozen=True)
class Cartera:
    criptos: list[Doble]  # de la que más le falta a la que menos
    total: float | None  # lo que tendría que subir todo a la vez, en %
    sin_coste: list[str]


def calcular(valores: list[Valor]) -> Cartera:
    # Es el equilibrio con el doble de precio: el orden y las que faltan no cambian.
    base = equilibrio.calcular(valores)
    criptos = [Doble(e.coin_id, e.precio, e.medio) for e in base.criptos]
    total = None
    if base.total is not None:
        total = ((base.total / 100 + 1) * 2 - 1) * 100
    return Cartera(criptos, total, base.sin_coste)
