"""/correlacion: si dos criptos suben y bajan a la vez."""

import math
from dataclasses import dataclass
from datetime import date, timedelta

from .periodo import PeriodoError, es_tramo, leer
from .simbolos import a_id

POR_DEFECTO = 30 * 24

EJEMPLO = "/correlacion btc eth 30d"

# Con menos cambios de día, una casualidad ya da una correlación muy alta.
MINIMO = 7


@dataclass(frozen=True)
class Correlacion:
    valor: float  # de -1 (al revés) a 1 (iguales)
    dias: int  # cuántos cambios de día se han comparado


def interpretar(argumento: str) -> tuple[list[str], float]:
    """'btc eth 7d' -> (['bitcoin', 'ethereum'], 168). Sin criptos, []."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if len(partes) not in (0, 2):
        raise PeriodoError(f"De dos en dos. Escríbelo así: {EJEMPLO}")
    ids = [a_id(p) for p in partes]
    if ids and ids[0] == ids[1]:
        raise PeriodoError("Son la misma cripto: claro que van juntas")
    return ids, horas


def _cambios(dias: list[tuple[date, float]]) -> dict[date, float]:
    """El % de cada día respecto al anterior, solo si hay precio de los dos."""
    precios = dict(dias)
    return {
        d: precios[d] / precios[d - timedelta(days=1)] - 1
        for d in precios
        if d - timedelta(days=1) in precios
    }


def calcular(
    una: list[tuple[date, float]], otra: list[tuple[date, float]]
) -> Correlacion | None:
    """None si no hay MINIMO días en común, o si una no se ha movido nada."""
    a, b = _cambios(una), _cambios(otra)
    comunes = sorted(a.keys() & b.keys())
    if len(comunes) < MINIMO:
        return None

    xs = [a[d] for d in comunes]
    ys = [b[d] for d in comunes]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if not vx or not vy:
        return None
    return Correlacion(cov / math.sqrt(vx * vy), len(comunes))
