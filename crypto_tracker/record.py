"""/record: lo máximo que ha valido tu cartera y cuánto le falta para volver."""

from dataclasses import dataclass
from datetime import datetime

# Si no borra nunca (HISTORY_DAYS=0), miro hasta diez años atrás.
SIN_LIMITE = 10 * 365 * 24


@dataclass(frozen=True)
class Record:
    maximo: float
    cuando: datetime
    ahora: float
    desde: datetime  # el primer precio que tengo

    @property
    def en_record(self) -> bool:
        return self.ahora >= self.maximo

    @property
    def falta(self) -> float:
        return self.maximo - self.ahora

    @property
    def caida(self) -> float:
        return (self.ahora / self.maximo - 1) * 100


def horas(history_days: int) -> float:
    return history_days * 24 if history_days else SIN_LIMITE


def calcular(serie: list[tuple[datetime, float]]) -> Record | None:
    """serie va del más viejo al más nuevo. None si no hay con qué comparar."""
    if len(serie) < 2:
        return None
    # Con max() se queda con el primero si hay empate: el récord es cuando se llegó.
    cuando, maximo = max(serie, key=lambda p: p[1])
    return Record(maximo, cuando, serie[-1][1], serie[0][0])
