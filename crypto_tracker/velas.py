"""/historico btc 7d velas: apertura, máximo, mínimo y cierre de cada rato."""

from dataclasses import dataclass
from datetime import datetime, timedelta

PALABRA = "velas"
# Con menos no se ve nada que no diga ya la línea.
MINIMO = 5


@dataclass(frozen=True)
class Vela:
    inicio: datetime
    apertura: float
    alto: float
    bajo: float
    cierre: float

    @property
    def sube(self) -> bool:
        return self.cierre >= self.apertura


def pedidas(argumento: str) -> tuple[bool, str]:
    """'btc 7d velas' -> (True, 'btc 7d'). Da igual dónde vaya la palabra."""
    partes = argumento.split()
    quiere = any(p.lower() == PALABRA for p in partes)
    return quiere, " ".join(p for p in partes if p.lower() != PALABRA)


def tamaño(horas: float) -> int:
    """Las horas de cada vela: que salgan entre 20 y 60 más o menos."""
    if horas <= 48:
        return 1
    if horas <= 10 * 24:
        return 4
    return 24


def agrupar(serie: list[tuple[datetime, float]], cada: int) -> list[Vela]:
    """En la hora de aquí: la vela de las 00:00 empieza a tu medianoche."""
    grupos: dict[datetime, list[float]] = {}
    for cuando, precio in serie:
        local = cuando.astimezone()
        inicio = local.replace(minute=0, second=0, microsecond=0)
        inicio -= timedelta(hours=inicio.hour % cada)
        grupos.setdefault(inicio, []).append(precio)
    return [
        Vela(inicio, p[0], max(p), min(p), p[-1])
        for inicio, p in sorted(grupos.items())
    ]
