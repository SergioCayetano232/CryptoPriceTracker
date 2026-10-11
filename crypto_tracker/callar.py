"""/mute bitcoin 2h: callar una sola cripto y que las demás sigan avisando."""

from datetime import datetime

from .config import ConfigError, minutos_mute
from .simbolos import IDS, a_id


def interpretar(argumento: str, ahora: datetime) -> tuple[str | None, int]:
    """'2h' -> (None, 120), todas. 'btc 2h' -> ('bitcoin', 120), solo esa."""
    try:
        return None, minutos_mute(argumento, ahora)
    except ConfigError as e:
        error = e

    # Si no es una duracion, lo primero tiene que ser la cripto.
    cripto, _, resto = argumento.strip().partition(" ")
    if cripto.lower() == "hasta":
        raise error
    if not resto.strip():
        # "/mute mucho" es un tiempo mal escrito, no una cripto que se llame asi.
        if a_id(cripto) not in IDS.values():
            raise error
        raise ConfigError(
            f"¿Cuánto tiempo? Por ejemplo: /mute {cripto} 2h "
            f"o /mute {cripto} hasta 8:00"
        )
    return a_id(cripto), minutos_mute(resto, ahora)
