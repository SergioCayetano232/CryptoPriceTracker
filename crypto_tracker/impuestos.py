"""/impuestos: lo que le tocaría a Hacienda de lo que has ganado vendiendo."""

from dataclasses import dataclass

from . import ganancias
from .movimientos import Movimiento

# Base del ahorro del IRPF desde 2025: hasta dónde llega cada tramo y su tipo.
TRAMOS = [
    (6_000, 19),
    (50_000, 21),
    (200_000, 23),
    (300_000, 27),
    (float("inf"), 30),
]


class ImpuestosError(Exception):
    """El año no se entiende."""


@dataclass(frozen=True)
class Impuestos:
    año: int
    ganancia: float
    tramos: list[tuple[int, float, float]]  # (tipo, lo que cae en él, lo que pagas)
    sin_datos: int  # ventas que no se pueden contar
    ventas: int

    @property
    def total(self) -> float:
        return sum(c for _, _, c in self.tramos)

    @property
    def tipo_medio(self) -> float:
        return self.total / self.ganancia * 100 if self.ganancia > 0 else 0


def interpretar(argumento: str, este_año: int) -> int:
    texto = argumento.strip()
    if not texto:
        return este_año
    if not texto.isdigit() or not 2009 <= int(texto) <= este_año:
        raise ImpuestosError(
            f"Dime un año entre 2009 y {este_año}, como /impuestos 2025"
        )
    return int(texto)


def por_tramos(ganancia: float) -> list[tuple[int, float, float]]:
    tramos, desde = [], 0.0
    for hasta, tipo in TRAMOS:
        if ganancia <= desde:
            break
        base = min(ganancia, hasta) - desde
        tramos.append((tipo, base, base * tipo / 100))
        desde = hasta
    return tramos


def calcular(ventas: list[Movimiento], año: int) -> Impuestos:
    del_año = [v for v in ventas if v.cuando.year == año]
    g = ganancias.calcular(del_año)
    return Impuestos(año, g.total, por_tramos(g.total), g.sin_datos, len(del_año))
