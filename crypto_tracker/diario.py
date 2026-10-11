"""Lo que depende de la hora del dia: el resumen y las horas tranquilas."""

from datetime import date, datetime, time, timedelta

from .config import ConfigError, parse_hora

# Si a la hora el bot estaba apagado, lo manda al volver, pero no mas tarde
# de esto. Un "buenos dias" a las once de la noche no pinta nada.
RETRASO_MAXIMO = timedelta(hours=2)


def toca_resumen(ahora: datetime, hora: time, ultimo: date | None) -> bool:
    """True si ya es la hora y hoy todavia no se ha mandado."""
    if ultimo == ahora.date():
        return False

    programado = datetime.combine(ahora.date(), hora, tzinfo=ahora.tzinfo)
    return programado <= ahora <= programado + RETRASO_MAXIMO


# Lo que vale en /horario para quedarse sin resumen.
SIN_RESUMEN = {"no", "nunca", "off", "quitar"}


def leer_hora(texto: str) -> time | None:
    """Lo que le pides a /horario: '8:30' -> 08:30, 'no' -> None, sin resumen."""
    texto = texto.strip().lower().removeprefix("a las ").strip()
    if texto in SIN_RESUMEN:
        return None
    try:
        hora = parse_hora(texto)
    except ConfigError:
        hora = None
    if hora is None:
        raise ConfigError(
            f"No entiendo '{texto}'. Por ejemplo: /horario 8:30, "
            "o /horario no para quitarlo"
        )
    return hora


def es_hora_tranquila(ahora: time, inicio: time, fin: time) -> bool:
    """True si `ahora` cae dentro del tramo, aunque cruce la medianoche."""
    if inicio < fin:
        return inicio <= ahora < fin
    # De 23 a 8: o ya es tarde, o todavia es temprano.
    return ahora >= inicio or ahora < fin
