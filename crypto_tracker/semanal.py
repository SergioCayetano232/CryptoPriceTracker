"""El resumen de la semana de la cartera, que llega los domingos."""

from dataclasses import dataclass
from datetime import date, datetime, time

from .cartera import serie_valor
from .config import Posicion
from .diario import toca_resumen

DOMINGO = 6
HORAS = 7 * 24


@dataclass(frozen=True)
class Semana:
    serie: list[tuple[datetime, float]]
    # (cripto, % en la semana), de la que mejor ha ido a la que peor
    cambios: list[tuple[str, float]]

    @property
    def inicio(self) -> float:
        return self.serie[0][1]

    @property
    def fin(self) -> float:
        return self.serie[-1][1]

    @property
    def ganancia(self) -> float:
        return self.fin - self.inicio

    @property
    def porcentaje(self) -> float | None:
        return self.ganancia / self.inicio * 100 if self.inicio else None


def toca(ahora: datetime, hora: time, ultimo: date | None) -> bool:
    """Lo mismo que el diario, pero solo los domingos."""
    return ahora.weekday() == DOMINGO and toca_resumen(ahora, hora, ultimo)


def semana(
    posiciones: list[Posicion], filas: list[tuple[datetime, str, float]]
) -> Semana | None:
    """Saca la semana de los precios guardados. None si no hay con que comparar."""
    serie = serie_valor(posiciones, filas)
    if len(serie) < 2:
        return None

    mias = {p.coin_id for p in posiciones}
    primero: dict[str, float] = {}
    ultimo: dict[str, float] = {}
    for _, coin_id, precio in filas:
        if coin_id in mias:
            primero.setdefault(coin_id, precio)
            ultimo[coin_id] = precio

    cambios = [
        (c, (ultimo[c] - primero[c]) / primero[c] * 100) for c in primero if primero[c]
    ]
    cambios.sort(key=lambda c: c[1], reverse=True)
    return Semana(serie, cambios)
