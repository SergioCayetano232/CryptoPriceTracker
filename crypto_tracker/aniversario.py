"""Las compras que cumplen años hoy, para recordarlas en el resumen del día."""

import calendar
from dataclasses import dataclass
from datetime import date

from .movimientos import Movimiento

# Si un día cumplen muchas, el resumen no puede llenarse solo de esto.
MAX = 3


@dataclass(frozen=True)
class Aniversario:
    compra: Movimiento
    años: int
    precio: float | None = None  # el de ahora; None si no lo tengo

    @property
    def valor(self) -> float | None:
        return None if self.precio is None else self.compra.cantidad * self.precio

    @property
    def cambio(self) -> float | None:
        if self.valor is None or not self.compra.coste:
            return None
        return (self.valor / self.compra.coste - 1) * 100


def _cumple(dia: date, hoy: date) -> int:
    """Los años que cumple hoy, o 0 si hoy no toca."""
    años = hoy.year - dia.year
    if años < 1:
        return 0
    # Lo del 29 de febrero se celebra el 28 los años que no son bisiestos.
    if dia.month == 2 and dia.day == 29 and not calendar.isleap(hoy.year):
        return años if (hoy.month, hoy.day) == (2, 28) else 0
    return años if (hoy.month, hoy.day) == (dia.month, dia.day) else 0


def de_hoy(movimientos: list[Movimiento], hoy: date) -> list[Movimiento]:
    """Las compras que cumplen años hoy, la más vieja primero."""
    compras = [
        m
        for m in movimientos
        if m.tipo == "compra" and _cumple(m.cuando.astimezone().date(), hoy)
    ]
    return sorted(compras, key=lambda m: m.id)


def calcular(
    compras: list[Movimiento], precios: dict[str, float], hoy: date
) -> list[Aniversario]:
    lista = []
    for m in compras:
        años = _cumple(m.cuando.astimezone().date(), hoy)
        lista.append(Aniversario(m, años, precios.get(m.coin_id)))
    return lista
