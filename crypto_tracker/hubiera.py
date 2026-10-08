"""/si: cuánto tendrías hoy si hubieras metido dinero hace un tiempo."""

from dataclasses import dataclass

from .alerts import SIMBOLOS
from .periodo import PeriodoError, leer
from .puntuales import numero
from .simbolos import a_id

POR_DEFECTO = 30 * 24

EJEMPLO = "/si 1000 bitcoin 30d"


@dataclass(frozen=True)
class Pregunta:
    cantidad: float
    coin_id: str
    horas: float


def interpretar(argumento: str, currency: str) -> Pregunta:
    """'1000 bitcoin 30d' -> Pregunta(1000, 'bitcoin', 720). Sin tramo, 30 dias."""
    # "1000 € bitcoin" o "1000 eur bitcoin" se entienden igual que "1000 bitcoin".
    sobra = {currency.lower(), SIMBOLOS.get(currency.lower())}
    partes = [p for p in argumento.lower().split() if p not in sobra]
    if len(partes) not in (2, 3):
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")

    cantidad = numero(partes[0])
    if cantidad is None or cantidad <= 0:
        raise PeriodoError(f"'{partes[0]}' no es una cantidad. Ej: {EJEMPLO}")

    horas = leer(partes[2]) if len(partes) == 3 else POR_DEFECTO
    return Pregunta(cantidad, a_id(partes[1]), horas)
