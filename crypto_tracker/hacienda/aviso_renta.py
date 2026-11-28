"""En abril, cuando abre la Renta, lo que vendiste el año pasado y cómo sacarlo."""

from datetime import date, datetime, time

from ..avisos.diario import toca_resumen
from .impuestos import Impuestos

# La campaña suele abrir a primeros de abril. Hasta el 15, por si ese día el bot
# está parado: lo intenta los siguientes.
AVISO_DESDE = 1
AVISO_HASTA = 15


def toca_aviso(ahora: datetime, hora: time, ultimo: date | None) -> bool:
    """Una vez al año, entre el 1 y el 15 de abril, a la hora del resumen."""
    local = ahora.astimezone()
    if local.month != 4 or not AVISO_DESDE <= local.day <= AVISO_HASTA:
        return False
    if ultimo is not None and ultimo.year == local.year:
        return False
    return toca_resumen(local, hora, ultimo)


def hay_que_declarar(i: Impuestos, recibido: float) -> bool:
    # Las pérdidas también: si no las declaras, no las puedes restar luego.
    return i.ventas > 0 or recibido > 0
