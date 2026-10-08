"""/volatilidad: cuanto se mueve una cripto, para elegir el % de /vigilar."""

from dataclasses import dataclass
from datetime import date, datetime

from .alerts import _revisar_porcentaje
from .config import Watch
from .periodo import PeriodoError, es_tramo, leer
from .simbolos import a_id

POR_DEFECTO = 30 * 24

# Los % que se prueban, de mucho aviso a poco.
PRUEBAS = (2, 5, 10)


@dataclass(frozen=True)
class Volatilidad:
    media: float  # lo que se mueve de media al dia, en %, sin signo
    peor: float  # el dia que mas se movio, con signo
    peor_dia: date
    dias: int  # cuantos cambios de dia se han contado


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 7d' -> ('bitcoin', 168). Sin tramo, 30 dias; sin cripto, ''."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if len(partes) > 1:
        raise PeriodoError("Escríbelo así: /volatilidad bitcoin 30d")
    # Con menos de dos dias no hay ni un cambio de un dia a otro.
    if horas < 48:
        raise PeriodoError("Necesito al menos 2 días, por ejemplo 7d")
    return (a_id(partes[0]) if partes else ""), horas


def por_dias(serie: list[tuple[datetime, float]]) -> list[tuple[date, float]]:
    """El ultimo precio de cada dia, en la hora de aqui."""
    dias: dict[date, float] = {}
    for cuando, precio in serie:
        dias[cuando.astimezone().date()] = precio
    return list(dias.items())


def calcular(serie: list[tuple[datetime, float]]) -> Volatilidad | None:
    """None si no hay al menos dos dias con precio."""
    dias = por_dias(serie)
    # Solo de un dia al siguiente: con el bot parado una semana, ese salto
    # no es lo que se mueve en un dia.
    cambios = [
        (dia, (precio / anterior - 1) * 100)
        for (ayer, anterior), (dia, precio) in zip(dias, dias[1:], strict=False)
        if anterior > 0 and (dia - ayer).days == 1
    ]
    if not cambios:
        return None

    media = sum(abs(c) for _, c in cambios) / len(cambios)
    peor_dia, peor = max(cambios, key=lambda c: abs(c[1]))
    return Volatilidad(media, peor, peor_dia, len(cambios))


def avisos(serie: list[tuple[datetime, float]], porcentaje: float) -> int:
    """Los avisos que habria mandado /vigilar con ese %, con la misma cuenta."""
    watch = Watch("simulada", percent=porcentaje)
    referencia, total = None, 0
    for _, precio in serie:
        alerta, referencia = _revisar_porcentaje(precio, watch, referencia)
        total += alerta is not None
    return total
