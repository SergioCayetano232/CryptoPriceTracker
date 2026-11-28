"""Qué pasó las otras veces que se movió así en un día, para la línea del aviso."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..volatilidad import por_dias

# Todo lo guardado; ya lo recorta HISTORY_DAYS.
HORAS = 366 * 24
DIAS_DESPUES = 7

# Moverse un 1% en un día pasa casi a diario, y eso no le dice nada a nadie.
MINIMO_MOVIMIENTO = 3.0
# Cuenta como "así" lo que se movió al menos el 80% de lo de hoy.
PARECIDO = 0.8
# Con dos casos, la media es casualidad.
MINIMO_VECES = 3


@dataclass(frozen=True)
class Contexto:
    sube: bool
    desde: float  # el % a partir del que cuenta como parecido, sin signo
    veces: int
    media: float  # lo que había cambiado DIAS_DESPUES más tarde, con signo
    siguio: int  # cuántas siguieron hacia el mismo lado
    dias: int  # lo que abarca lo guardado: "3 veces" en un mes no es en un año


def buscar(serie: list[tuple[datetime, float]], variacion: float) -> Contexto | None:
    """None si el movimiento es pequeño o no hay bastantes casos."""
    if abs(variacion) < MINIMO_MOVIMIENTO:
        return None

    sube = variacion > 0
    desde = abs(variacion) * PARECIDO
    cierres = dict(por_dias(serie))

    despues = []
    saltar_hasta = None
    for dia, precio in cierres.items():
        if saltar_hasta and dia <= saltar_hasta:
            continue
        ayer = cierres.get(dia - timedelta(days=1))
        luego = cierres.get(dia + timedelta(days=DIAS_DESPUES))
        if not ayer or luego is None:
            continue
        cambio = (precio / ayer - 1) * 100
        if (cambio > 0) != sube or abs(cambio) < desde:
            continue
        despues.append((luego / precio - 1) * 100)
        # Una racha de días fuertes es una sola vez, no cinco que se solapan.
        saltar_hasta = dia + timedelta(days=DIAS_DESPUES)

    if len(despues) < MINIMO_VECES:
        return None
    siguio = sum((d > 0) == sube for d in despues)
    dias = (max(cierres) - min(cierres)).days + 1
    media = sum(despues) / len(despues)
    return Contexto(sube, desde, len(despues), media, siguio, dias)
