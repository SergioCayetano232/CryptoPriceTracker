"""/hoy: cómo van desde las 00:00, no en las últimas 24 h."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Hoy:
    antes: float  # el último de ayer o, si no lo hay, el primero de hoy
    ahora: float
    maximo: float
    minimo: float
    desde: datetime | None  # solo si no tengo el de las 00:00

    @property
    def cambio(self) -> float:
        return (self.ahora / self.antes - 1) * 100


def medianoche(ahora: datetime) -> datetime:
    """Las 00:00 de hoy en la hora de aquí."""
    return ahora.astimezone().replace(hour=0, minute=0, second=0, microsecond=0)


def calcular(serie: list[tuple[datetime, float]], desde: datetime) -> Hoy | None:
    """serie tiene que llegar un poco antes de desde. None si no hay nada de hoy."""
    antes = [p for t, p in serie if t < desde]
    hoy = [(t, p) for t, p in serie if t >= desde]
    if not hoy:
        return None

    precios = [p for _, p in hoy]
    # Sin el de antes de las 00:00 (bot apagado), cuento desde el primero de hoy.
    if antes:
        return Hoy(antes[-1], precios[-1], max(precios), min(precios), None)
    return Hoy(precios[0], precios[-1], max(precios), min(precios), hoy[0][0])


def mejor_y_peor(lineas: list[tuple[str, Hoy | None]]) -> tuple[str, str] | None:
    """Las ids de la que mejor va hoy y la que peor. None si no hay con qué comparar."""
    # Las que empiezan más tarde de las 00:00 miden otro tramo: no cuentan.
    completas = [(c, h.cambio) for c, h in lineas if h and h.desde is None]
    if len(completas) < 3:
        return None
    completas.sort(key=lambda x: x[1])
    if completas[0][1] == completas[-1][1]:
        return None
    return completas[-1][0], completas[0][0]
