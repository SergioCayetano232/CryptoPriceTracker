"""Aviso de cuando la cartera cae mucho desde su récord, sin tener que preguntar."""

import math
from datetime import datetime

from .record import Record


def escalon(r: Record, porcentaje: float) -> int:
    """Cuántas veces ha caído el porcentaje: con un 20%, un -45% es el 2."""
    if r.en_record:
        return 0
    # El redondeo evita que un -40% justo se quede en 1 por los decimales.
    return math.floor(round(-r.caida / porcentaje, 9))


def toca(
    r: Record, porcentaje: float, avisado: tuple[datetime, int] | None
) -> int | None:
    """El escalón del que avisar, o None si no hay nada nuevo.

    avisado es (cuándo fue el récord, escalón) del último aviso que llegó.
    """
    ahora = escalon(r, porcentaje)
    if not ahora:
        return None
    # Con un récord nuevo lo de antes ya no cuenta y se empieza de cero.
    ya = avisado[1] if avisado and avisado[0] == r.cuando else 0
    return ahora if ahora > ya else None
