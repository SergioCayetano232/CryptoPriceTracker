"""/quieta: la que menos se ha movido en las últimas 24 h de las que vigilo."""

from dataclasses import dataclass
from datetime import datetime

HORAS = 24


@dataclass(frozen=True)
class Quieta:
    coin_id: str
    minimo: float
    maximo: float

    @property
    def rango(self) -> float:
        """Del mínimo al máximo, en %."""
        return (self.maximo / self.minimo - 1) * 100


def calcular(series: dict[str, list[tuple[datetime, float]]]) -> list[Quieta]:
    # Del mínimo al máximo y no cómo acaba: subir un 5% y volver no es estar quieta.
    quietas = []
    for coin_id, serie in series.items():
        precios = [p for _, p in serie if p > 0]
        if len(precios) < 2:
            continue
        quietas.append(Quieta(coin_id, min(precios), max(precios)))
    return sorted(quietas, key=lambda q: q.rango)
