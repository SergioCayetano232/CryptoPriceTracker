"""/mes y /anual: cómo va la cartera desde el día 1 o desde el 1 de enero."""

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
    aqui = ahora.astimezone()
    # Sin pasar por la hora sin zona, tras el cambio de hora saldría una hora movida.
    return datetime(aqui.year, aqui.month, 1).astimezone()


def horas(ahora: datetime) -> float:
    return (ahora - principio(ahora)).total_seconds() / 3600


def nombre(ahora: datetime) -> str:
    return MESES[ahora.astimezone().month - 1]


def principio_del_ano(ahora: datetime) -> datetime:
    return datetime(ahora.astimezone().year, 1, 1).astimezone()


def horas_del_ano(ahora: datetime) -> float:
    return (ahora - principio_del_ano(ahora)).total_seconds() / 3600


def pista(history_days: int, horas: float) -> str | None:
    """Qué tocar si el bot borra los precios antes de lo que se le pide."""
    # Con 0 no borra nada: si falta el principio, es que aún no estaba encendido.
    if not history_days or history_days * 24 >= horas:
        return None
    return (
        f"Solo guardo {history_days} días de precios. Para tener el año entero, "
        "pon HISTORY_DAYS=366 en el .env"
    )
