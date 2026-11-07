"""Tu año en cripto: llega el 1 de enero, y con /anual 2026 cuando quieras."""

from dataclasses import dataclass
from datetime import date, datetime, time

from .compras import Resumen
from .compras import calcular as calcular_compras
from .config import Posicion
from .diario import toca_resumen
from .ganancias import calcular as calcular_ganancias
from .movimientos import Movimiento
from .semanal import Semana, semana


class AnualError(Exception):
    """El año no se entiende."""


@dataclass(frozen=True)
class Año:
    año: int
    cartera: Semana | None  # None sin dos precios guardados del año
    meses: list[tuple[int, float]]  # (mes, %) de los que hay precios
    compras: int
    comprado: float
    ventas: int
    vendido: float
    ganado: float  # lo ganado vendiendo, como /ganancias
    mis_compras: Resumen | None  # la mejor y la peor, al precio del final del año

    @property
    def mejor_mes(self) -> tuple[int, float] | None:
        # Con uno solo, "el mejor" y "el peor" serían el mismo.
        return max(self.meses, key=lambda m: m[1]) if len(self.meses) > 1 else None

    @property
    def peor_mes(self) -> tuple[int, float] | None:
        return min(self.meses, key=lambda m: m[1]) if len(self.meses) > 1 else None

    @property
    def desde(self) -> date | None:
        """El primer día con precios, para decir si falta el principio del año."""
        return self.cartera.serie[0][0].astimezone().date() if self.cartera else None


def toca(ahora: datetime, hora: time, ultimo: date | None) -> bool:
    """Lo mismo que el diario, pero solo el 1 de enero."""
    local = ahora.astimezone()
    return (local.month, local.day) == (1, 1) and toca_resumen(ahora, hora, ultimo)


def interpretar(argumento: str, este_año: int) -> int:
    texto = argumento.strip()
    if not texto.isdigit() or not 2009 <= int(texto) <= este_año:
        raise AnualError(f"Dime un año entre 2009 y {este_año}, como /anual {este_año}")
    return int(texto)


def tramo(año: int) -> tuple[datetime, datetime]:
    """Del 1 de enero a las 00:00 al 1 de enero siguiente, sin incluirlo."""
    desde = datetime(año, 1, 1).astimezone()
    return desde, datetime(año + 1, 1, 1).astimezone()


def meses(serie: list[tuple[datetime, float]]) -> list[tuple[int, float]]:
    """Lo que cambió la cartera cada mes, del primer precio del mes al último."""
    por_mes: dict[int, list[float]] = {}
    for cuando, valor in serie:
        por_mes.setdefault(cuando.astimezone().month, []).append(valor)
    return [
        (mes, (v[-1] / v[0] - 1) * 100)
        for mes, v in sorted(por_mes.items())
        if len(v) > 1 and v[0]
    ]


def calcular(
    año: int,
    posiciones: list[Posicion],
    filas: list[tuple[datetime, str, float]],
    movimientos: list[Movimiento],
) -> Año:
    """filas son los precios guardados del año, ya recortados a su tramo."""
    cartera = semana(posiciones, filas)
    del_año = [m for m in movimientos if m.cuando.astimezone().year == año]
    compras = [m for m in del_año if m.tipo == "compra"]
    ventas = [m for m in del_año if m.tipo == "venta"]

    # Las compras se miran con el último precio del año: las de 2025 se juzgan
    # a 31 de diciembre de 2025, no a lo que valen hoy.
    al_final = {coin_id: precio for _, coin_id, precio in filas}
    return Año(
        año=año,
        cartera=cartera,
        meses=meses(cartera.serie) if cartera else [],
        compras=len(compras),
        comprado=sum(m.coste for m in compras if m.coste),
        ventas=len(ventas),
        vendido=sum(m.coste for m in ventas if m.coste),
        ganado=calcular_ganancias(ventas).total,
        mis_compras=calcular_compras(compras, al_final),
    )
