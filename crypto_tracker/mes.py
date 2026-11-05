"""/mes: cómo va la cartera desde el día 1, no en los últimos 30 días."""

from datetime import datetime

MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def principio(ahora: datetime) -> datetime:
    """El día 1 a las 00:00, en la hora de aquí."""
    return ahora.astimezone().replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def horas(ahora: datetime) -> float:
    return (ahora - principio(ahora)).total_seconds() / 3600


def nombre(ahora: datetime) -> str:
    return MESES[ahora.astimezone().month - 1]
