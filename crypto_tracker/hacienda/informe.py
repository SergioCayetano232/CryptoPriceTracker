"""/informe: el año fiscal en un PDF, para guardarlo o dárselo al gestor.

Aquí solo se juntan las cuentas, que ya hacen /impuestos y /comisiones. El
dibujo va en informe_pdf.py.
"""

from dataclasses import dataclass

from .. import comisiones
from ..comisiones import Comisiones
from ..movimientos import Movimiento
from . import impuestos, renta
from .impuestos import Impuestos
from .renta import Venta

EJEMPLO = "/informe 2025"

# Las ventas que caben en una hoja de la tabla.
POR_HOJA = 32


class InformeError(Exception):
    """El año no se entiende."""


@dataclass(frozen=True)
class Informe:
    año: int
    ventas: list[Venta]
    impuestos: Impuestos
    recompensas: float  # lo que valían al llegar las de ese año
    comisiones: Comisiones
    por_mes: list[float]  # la ganancia de cada mes, de enero a diciembre
    por_cripto: list[tuple[str, float]]  # de la que más ganó a la que más perdió

    @property
    def contadas(self) -> list[Venta]:
        """Las que tienen precio y coste: las demás no entran en ningún total."""
        return [v for v in self.ventas if v.ganancia is not None]

    @property
    def transmision(self) -> float:
        return sum(v.transmision for v in self.contadas)

    @property
    def adquisicion(self) -> float:
        return sum(v.adquisicion for v in self.contadas)

    @property
    def vacio(self) -> bool:
        return not self.ventas and not self.recompensas


def interpretar(argumento: str, este_año: int) -> int:
    try:
        return impuestos.interpretar(argumento, este_año)
    except impuestos.ImpuestosError:
        raise InformeError(
            f"Dime un año entre 2009 y {este_año}, como {EJEMPLO}"
        ) from None


def montar(movimientos: list[Movimiento], año: int) -> Informe:
    """movimientos son todos, de cualquier año: el coste sale de compras viejas."""
    # Por fecha y no por número: las de /importar entran desordenadas.
    ventas = sorted(renta.ventas(movimientos, año), key=lambda v: (v.cuando, v.numero))
    por_mes = [0.0] * 12
    por_cripto: dict[str, float] = {}
    for v in ventas:
        if v.ganancia is None:
            continue
        # En UTC, igual que se decide a qué año va: si no, una venta de
        # Nochevieja podría caer en un mes de otro año.
        por_mes[v.cuando.month - 1] += v.ganancia
        por_cripto[v.coin_id] = por_cripto.get(v.coin_id, 0.0) + v.ganancia

    return Informe(
        año=año,
        ventas=ventas,
        impuestos=impuestos.calcular(movimientos, año),
        recompensas=impuestos.recompensas_de(movimientos, año),
        comisiones=comisiones.calcular(movimientos, año),
        por_mes=por_mes,
        por_cripto=sorted(por_cripto.items(), key=lambda c: -c[1]),
    )


def hojas(ventas: list[Venta]) -> list[list[Venta]]:
    """Las ventas partidas en las hojas de la tabla."""
    return [ventas[i : i + POR_HOJA] for i in range(0, len(ventas), POR_HOJA)]


def nombre(año: int) -> str:
    return f"informe-{año}.pdf"
