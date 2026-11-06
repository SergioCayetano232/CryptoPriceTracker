"""El resumen del mes que acaba de terminar, que llega el día 1."""

from datetime import date, datetime, time, timedelta

from .diario import toca_resumen
from .mes import principio


def toca(ahora: datetime, hora: time, ultimo: date | None) -> bool:
    """Lo mismo que el diario, pero solo el día 1."""
    return ahora.astimezone().day == 1 and toca_resumen(ahora, hora, ultimo)


def tramo(ahora: datetime) -> tuple[datetime, datetime]:
    """Del 1 del mes pasado a las 00:00 al 1 de este, sin incluirlo."""
    hasta = principio(ahora)
    # Un día antes del 1 siempre cae en el mes anterior, tenga 28 o 31.
    return principio(hasta - timedelta(days=1)), hasta
