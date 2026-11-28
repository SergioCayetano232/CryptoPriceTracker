"""Lo que depende de la hora del dia: el resumen y las horas tranquilas."""

from datetime import date, datetime, time, timedelta

from .nucleo.config import ConfigError, parse_hora

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


def leer_dormir(texto: str) -> tuple[time, time] | None:
    """Lo de /dormir: '23-8', '23:30 7' o 'de 23 a 8'. 'no' es que suenen siempre."""
    texto = texto.strip().lower()
    if texto in SIN_RESUMEN:
        return None
    partes = texto.removeprefix("de ").replace(" a ", " ").replace("-", " ").split()
    error = ConfigError(
        f"No entiendo '{texto}'. Por ejemplo: /dormir 23-8, /dormir 23:30 7:00 "
        "o /dormir no para que suenen siempre"
    )
    if len(partes) != 2:
        raise error
    try:
        inicio, fin = parse_hora(partes[0]), parse_hora(partes[1])
    except ConfigError:
        raise error from None
    if inicio == fin:
        raise ConfigError("Empieza y acaba a la misma hora. Por ejemplo: /dormir 23-8")
    return inicio, fin


def es_hora_tranquila(ahora: time, inicio: time, fin: time) -> bool:
    """True si `ahora` cae dentro del tramo, aunque cruce la medianoche."""
    if inicio < fin:
        return inicio <= ahora < fin
    # De 23 a 8: o ya es tarde, o todavia es temprano.
    return ahora >= inicio or ahora < fin
