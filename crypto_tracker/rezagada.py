"""/rezagada: avisa cuando una lleva una semana haciéndolo mucho peor que otra."""

from dataclasses import dataclass

from .nucleo.simbolos import a_id
from .puntuales import numero

EJEMPLO = "/rezagada eth btc 10"
HORAS = 7 * 24
QUITAR = {"no", "quitar", "off"}


class RezagadaError(Exception):
    """Lo que escribiste en /rezagada no se entiende."""


@dataclass(frozen=True)
class Rezagada:
    coin_id: str
    contra: str
    porcentaje: float
    avisada: bool = False


def interpretar(argumento: str) -> tuple[str, str, float | None]:
    """'eth btc 10' -> ('ethereum', 'bitcoin', 10). Con 'no' al final, None."""
    partes = argumento.split()
    if len(partes) != 3:
        raise RezagadaError(f"Escríbelo así: {EJEMPLO} (la que miro, contra cuál, %)")
    coin_id, contra = a_id(partes[0]), a_id(partes[1])
    if coin_id == contra:
        raise RezagadaError("Son la misma, pon dos distintas.")
    if partes[2].lower() in QUITAR:
        return coin_id, contra, None
    pct = numero(partes[2].rstrip("%"))
    if pct is None or not 0 < pct < 100:
        raise RezagadaError(f"'{partes[2]}' no es un %. Por ejemplo: {EJEMPLO}")
    return coin_id, contra, pct


def diferencia(ahora: float, antes: float, contra_ahora: float, contra_antes: float):
    """Cuánto peor (negativo) o mejor lo ha hecho una que la otra, en %."""
    return ((ahora / antes) / (contra_ahora / contra_antes) - 1) * 100


def toca(r: Rezagada, dif: float) -> tuple[bool, bool]:
    """(toca avisar, queda avisada)."""
    if r.avisada:
        # Hasta que recupere la mitad, para no avisar a cada vaivén.
        return False, dif <= -r.porcentaje / 2
    return dif <= -r.porcentaje, dif <= -r.porcentaje
