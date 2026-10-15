"""/equilibrio: a qué precio dejas de perder con cada cripto de la cartera."""

from dataclasses import dataclass

from .cartera import Valor


@dataclass(frozen=True)
class Equilibrio:
    coin_id: str
    precio: float  # el de ahora
    medio: float  # a cuánto te salió: por encima, ganas

    @property
    def falta(self) -> float:
        """Lo que tiene que moverse, en %. Negativo si ya ganas."""
        return (self.medio / self.precio - 1) * 100


@dataclass(frozen=True)
class Cartera:
    criptos: list[Equilibrio]  # de la que más le falta a la que menos
    total: float | None  # lo que tendría que subir todo a la vez, en %
    sin_coste: list[str]  # las que no dicen lo que costaron


def calcular(valores: list[Valor]) -> Cartera:
    criptos, sin_coste = [], []
    for v in valores:
        if v.precio_medio is None or not v.precio:
            sin_coste.append(v.coin_id)
            continue
        criptos.append(Equilibrio(v.coin_id, v.precio, v.precio_medio))
    criptos.sort(key=lambda e: e.falta, reverse=True)

    # El total solo vale si sé lo que costó todo: si no, saldría de menos.
    total = None
    valor = sum(v.valor for v in valores)
    if criptos and not sin_coste and valor:
        total = (sum(v.invertido for v in valores) / valor - 1) * 100
    return Cartera(criptos, total, sin_coste)
