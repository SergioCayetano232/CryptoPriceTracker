"""/mute bitcoin 2h: callar una sola cripto y que las demás sigan avisando."""

import html
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


def a_secas(hasta: datetime | None, calladas: dict[str, datetime]) -> str:
    """/mute sin nada: lo que tengo callado ahora y la pregunta de cuánto."""
    lineas = []
    if hasta:
        lineas.append(
            f"🔕 Ya estoy callado hasta las {hasta.astimezone():%H:%M del %d/%m}."
        )
    if calladas:
        lineas.append(
            "Y aparte, cada una por su lado:" if hasta else "🔕 Ahora no te aviso de:"
        )
        # La que antes vuelve a avisar, primero.
        for coin_id, cuando in sorted(calladas.items(), key=lambda x: x[1]):
            nombre = html.escape(coin_id.replace("-", " ").title())
            lineas.append(
                f"<b>{nombre}</b> hasta las {cuando.astimezone():%H:%M del %d/%m} "
                f"· /unmute {html.escape(coin_id)}"
            )

    if hasta:
        lineas.append(("\n" if calladas else "") + "¿Vuelvo a avisar o lo cambio?")
    elif calladas:
        lineas.append("\n¿Cuánto tiempo me callo con todas?")
    else:
        lineas.append("🔕 ¿Cuánto tiempo me callo?")
    return "\n".join(lineas)
