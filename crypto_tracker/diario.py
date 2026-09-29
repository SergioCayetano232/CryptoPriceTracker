"""Decide cuando toca mandar el resumen del dia."""

from datetime import date, datetime, time, timedelta

# Si a la hora el bot estaba apagado, lo manda al volver, pero no mas tarde
# de esto. Un "buenos dias" a las once de la noche no pinta nada.
RETRASO_MAXIMO = timedelta(hours=2)


def toca_resumen(ahora: datetime, hora: time, ultimo: date | None) -> bool:
    """True si ya es la hora y hoy todavia no se ha mandado."""
    if ultimo == ahora.date():
        return False

    programado = datetime.combine(ahora.date(), hora, tzinfo=ahora.tzinfo)
    return programado <= ahora <= programado + RETRASO_MAXIMO
