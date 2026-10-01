"""El tramo de tiempo de /historico: leerlo y decirlo bien."""

from datetime import datetime, timedelta

from .config import ConfigError, parse_duracion

POR_DEFECTO = 24

# Mas de un año no cabe en una grafica de movil y tampoco se suele guardar.
MAXIMO = 366 * 24


class PeriodoError(Exception):
    """El tramo de /historico no se entiende."""


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 7d' -> ('bitcoin', 168). Sin tramo son 24 h."""
    partes = argumento.split()
    if not partes:
        return "", POR_DEFECTO
    if len(partes) > 2:
        raise PeriodoError("Escríbelo así: /historico bitcoin 7d")

    coin_id = partes[0].lower()
    if len(partes) == 1:
        return coin_id, POR_DEFECTO

    try:
        horas = parse_duracion(partes[1]) / 60
    except ConfigError as e:
        raise PeriodoError(str(e)) from None

    if horas > MAXIMO:
        raise PeriodoError("Como mucho un año: /historico bitcoin 365d")
    return coin_id, horas


def nombre(horas: float) -> str:
    """'últimas 24 h', 'últimos 7 días', 'últimos 30 min'."""
    if horas < 1:
        return f"últimos {round(horas * 60)} min"
    if horas == 1:
        return "última hora"
    # 24 y 36 se entienden mejor en horas; a partir de dos dias, en dias.
    if horas >= 48 and horas % 24 == 0:
        return f"últimos {int(horas // 24)} días"
    return f"últimas {horas:g} h".replace(".", ",")


def falta_principio(primero: datetime, ahora: datetime, horas: float) -> bool:
    """True si el primer precio guardado llega bastante despues de lo pedido."""
    pedido = ahora - timedelta(hours=horas)
    # Un ciclo de retraso es normal; un 5% del tramo (o una hora) ya no.
    margen = max(timedelta(hours=1), timedelta(hours=horas) * 0.05)
    return primero - pedido > margen
