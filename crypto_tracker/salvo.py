"""/mute 7d salvo 10%: callado, pero si alguna se mueve mucho, te enteras."""

import re
from datetime import datetime, timedelta

from .config import ConfigError
from .mensajes.base import SIMBOLOS, _flecha, _nombre, _num
from .puntuales import numero

# Una vez al día por cripto: si se queda un -15% toda la semana, no quiero
# que te escriba cada cinco minutos estando de vacaciones.
CADA = timedelta(hours=24)

_SALVO = re.compile(r"\s+salvo\s+(\S+)\s*$", re.IGNORECASE)


def interpretar(argumento: str) -> tuple[str, float | None]:
    """'7d salvo 10%' -> ('7d', 10). Sin salvo, (argumento, None)."""
    encontrado = _SALVO.search(argumento)
    if not encontrado:
        if argumento.strip().lower().startswith("salvo"):
            raise ConfigError("Primero cuánto tiempo: /mute 7d salvo 10%")
        return argumento, None

    pct = numero(encontrado.group(1).removesuffix("%"))
    if pct is None or not 1 <= pct <= 100:
        raise ConfigError("Lo de salvo va de 1% a 100%, como /mute 7d salvo 10%")
    return argumento[: encontrado.start()], pct


def toca(
    variacion: float | None,
    umbral: float,
    ultimo: datetime | None,
    ahora: datetime,
) -> bool:
    if variacion is None or abs(variacion) < umbral:
        return False
    return ultimo is None or ahora - ultimo >= CADA


def texto(
    coin_id: str, precio: float, variacion: float, currency: str, hasta: datetime
) -> str:
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    pct = f"{variacion:+.1f}%".replace(".", ",")
    return (
        f"🚨 <b>{_nombre(coin_id)}</b> {_flecha(variacion)} {pct} en 24 h, "
        f"ahora {simbolo}{_num(precio)}\n"
        f"<i>Te lo digo aunque estoy callado hasta el "
        f"{hasta.astimezone():%d/%m a las %H:%M}. /unmute para volver.</i>"
    )
