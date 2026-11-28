"""/mitad: a qué precio pierdes la mitad de lo que metiste en cada cripto."""

from dataclasses import dataclass

from . import equilibrio
from .cartera import Valor


@dataclass(frozen=True)
class Mitad:
    coin_id: str
    precio: float  # el de ahora
    medio: float  # a cuánto te salió

    @property
    def objetivo(self) -> float:
        return self.medio / 2

    @property
    def aguanta(self) -> float:
        """Lo que puede bajar hasta ahí, en %. Negativo si ya está por debajo."""
        return (1 - self.objetivo / self.precio) * 100


@dataclass(frozen=True)
class Cartera:
    criptos: list[Mitad]  # de la que más cerca está a la que menos
    total: float | None  # lo que puede bajar todo a la vez, en %
    sin_coste: list[str]


def calcular(valores: list[Valor]) -> Cartera:
    # Sale del equilibrio: la que más lejos está de recuperar es la más cerca de aquí.
    base = equilibrio.calcular(valores)
    criptos = [Mitad(e.coin_id, e.precio, e.medio) for e in base.criptos]
    total = None
    if base.total is not None:
        total = (1 - (base.total / 100 + 1) / 2) * 100
    return Cartera(criptos, total, base.sin_coste)
