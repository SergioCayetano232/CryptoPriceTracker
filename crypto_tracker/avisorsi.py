"""Aviso de cuando una cripto que vigilas entra en sobrecompra o sobreventa."""

from .rsi import SOBRECOMPRA, SOBREVENTA

ALTA = "alta"
BAJA = "baja"

# Lo que tiene que alejarse para volver a avisar. El precio de hoy aún se mueve
# y, rondando el 70, entraría y saldría varias veces en un día.
MARGEN = 5


def zona(valor: float) -> str | None:
    if valor >= SOBRECOMPRA:
        return ALTA
    return BAJA if valor <= SOBREVENTA else None


def toca(valor: float, avisado: str | None) -> str | None:
    """La zona de la que hay que avisar. None si no hay nada nuevo."""
    actual = zona(valor)
    return actual if actual != avisado else None


def sigue(valor: float, avisado: str | None) -> str | None:
    """Si no toca avisar, lo que se queda apuntado: lo de antes o nada."""
    if avisado == ALTA and valor >= SOBRECOMPRA - MARGEN:
        return ALTA
    if avisado == BAJA and valor <= SOBREVENTA + MARGEN:
        return BAJA
    return None
