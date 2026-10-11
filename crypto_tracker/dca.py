"""/dca: cuánto tendrías si hubieras metido lo mismo cada semana (o cada día, o mes)."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .alerts import SIMBOLOS
from .periodo import PeriodoError, es_tramo, leer
from .puntuales import numero
from .simbolos import a_id

POR_DEFECTO = 90 * 24

EJEMPLO = "/dca 50 bitcoin semanal 90d"

# Un mes son 30 días: con meses de verdad la cuenta cambiaría según cuándo preguntes.
CADA = {"diario": 24, "semanal": 7 * 24, "mensual": 30 * 24}
TEXTO = {"diario": "cada día", "semanal": "cada semana", "mensual": "cada mes"}


@dataclass(frozen=True)
class Plan:
    cantidad: float
    coin_id: str
    frecuencia: str  # diario, semanal o mensual
    horas: float

    @property
    def cada(self) -> float:
        """Horas entre compra y compra."""
        return CADA[self.frecuencia]


@dataclass(frozen=True)
class Resultado:
    compras: int
    cripto: float
    valor: float


def interpretar(argumento: str, currency: str) -> Plan:
    """'50 bitcoin semanal 90d' -> Plan(50, 'bitcoin', 'semanal', 2160).

    Sin frecuencia, semanal; sin tramo, 90 días. Esos dos en el orden que sea.
    """
    sobra = {currency.lower(), SIMBOLOS.get(currency.lower())}
    partes = [p for p in argumento.lower().split() if p not in sobra]
    if not 2 <= len(partes) <= 4:
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")

    cantidad = numero(partes[0])
    if cantidad is None or cantidad <= 0:
        raise PeriodoError(f"'{partes[0]}' no es una cantidad. Ej: {EJEMPLO}")

    frecuencia, horas = "semanal", None
    for parte in partes[2:]:
        if parte in CADA:
            frecuencia = parte
        elif es_tramo(parte) and horas is None:
            horas = leer(parte)
        else:
            raise PeriodoError(
                f"No entiendo '{parte}'. Cada cuánto: diario, semanal o mensual. "
                f"Ej: {EJEMPLO}"
            )

    horas = POR_DEFECTO if horas is None else horas
    if horas < CADA[frecuencia]:
        raise PeriodoError("Así solo sale una compra: para eso está /si")
    return Plan(cantidad, a_id(partes[1]), frecuencia, horas)


def calcular(
    serie: list[tuple[datetime, float]], cantidad: float, cada: float
) -> Resultado:
    """Compra al primer precio guardado de cada tramo. La serie no puede ir vacía."""
    cripto = 0.0
    compras = 0
    siguiente = serie[0][0]
    for cuando, precio in serie:
        # Con el bot parado unos días se salta esas compras, no las junta todas.
        if cuando >= siguiente and precio > 0:
            cripto += cantidad / precio
            compras += 1
            while siguiente <= cuando:
                siguiente += timedelta(hours=cada)

    return Resultado(compras, cripto, cripto * serie[-1][1])
