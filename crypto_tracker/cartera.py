"""Cuanto vale lo que tienes y cuanto llevas ganado o perdido."""

from dataclasses import dataclass

from .config import Posicion


@dataclass(frozen=True)
class Valor:
    coin_id: str
    valor: float
    invertido: float | None = None

    @property
    def ganancia(self) -> float | None:
        return None if self.invertido is None else self.valor - self.invertido

    @property
    def porcentaje(self) -> float | None:
        if not self.invertido:
            return None
        return self.ganancia / self.invertido * 100


def valorar(
    posiciones: list[Posicion], precios: dict[str, float]
) -> tuple[list[Valor], list[str]]:
    """Valora cada posicion. Devuelve tambien las que se quedaron sin precio."""
    valores, faltan = [], []

    for p in posiciones:
        precio = precios.get(p.coin_id)
        if precio is None:
            faltan.append(p.coin_id)
            continue
        valores.append(Valor(p.coin_id, p.cantidad * precio, p.invertido))

    return valores, faltan


def total(valores: list[Valor]) -> Valor:
    """La suma. Si alguna no dice lo que costo, el total tampoco puede."""
    invertido = None
    if valores and all(v.invertido is not None for v in valores):
        invertido = sum(v.invertido for v in valores)
    return Valor("total", sum(v.valor for v in valores), invertido)
