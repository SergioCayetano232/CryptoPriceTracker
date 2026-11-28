"""Lo que ha pasado mientras el bot estaba callado, para contártelo al volver."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Movida:
    coin_id: str
    antes: float
    ahora: float
    maximo: float
    minimo: float

    @property
    def cambio(self) -> float:
        return (self.ahora / self.antes - 1) * 100


@dataclass(frozen=True)
class Perdido:
    desde: datetime
    hasta: datetime
    movidas: list[Movida]  # de la que más se ha movido a la que menos
    cartera: float | None  # en %; None sin cartera o sin precios de todo

    @property
    def tiempo(self):
        return self.hasta - self.desde


def movida(coin_id: str, serie: list[tuple[datetime, float]]) -> Movida | None:
    if len(serie) < 2 or serie[0][1] <= 0:
        return None
    precios = [p for _, p in serie]
    return Movida(coin_id, precios[0], precios[-1], max(precios), min(precios))


def calcular(
    desde: datetime,
    hasta: datetime,
    series: dict[str, list[tuple[datetime, float]]],
    serie_cartera: list[tuple[datetime, float]],
) -> Perdido:
    movidas = [m for c, s in series.items() if (m := movida(c, s))]
    movidas.sort(key=lambda m: abs(m.cambio), reverse=True)
    cartera = None
    if len(serie_cartera) >= 2 and serie_cartera[0][1] > 0:
        cartera = (serie_cartera[-1][1] / serie_cartera[0][1] - 1) * 100
    return Perdido(desde, hasta, movidas, cartera)
