"""/sivendo: lo que ganarías y lo que le tocaría a Hacienda, antes de vender."""

from dataclasses import dataclass

from . import ganancias
from .config import Posicion
from .impuestos import Impuestos, por_tramos
from .movimientos import MovimientoError, cobrado, interpretar_venta

EJEMPLO = (
    "/sivendo bitcoin 0.005, /sivendo bitcoin todo o /sivendo bitcoin 0.005 @80000"
)


@dataclass(frozen=True)
class Simulacion:
    coin_id: str
    vendido: float
    cobrado: float
    coste: float | None  # None si no sabes lo que te costó
    queda: float
    ya_ganado: float  # lo de este año, antes de esta venta
    sin_datos: int  # ventas de este año que no se pueden contar

    @property
    def ganancia(self) -> float | None:
        return None if self.coste is None else self.cobrado - self.coste

    @property
    def porcentaje(self) -> float | None:
        return self.ganancia / self.coste * 100 if self.coste else None

    @property
    def hacienda(self) -> float | None:
        """Lo que sube la cuenta del año. Negativo si esta venta la baja."""
        if self.ganancia is None:
            return None
        # Sobre lo que ya llevas: vender poco puede caer ya en un tramo más caro.
        return _cuota(self.ya_ganado + self.ganancia) - _cuota(self.ya_ganado)


def _cuota(ganancia: float) -> float:
    return sum(c for _, _, c in por_tramos(ganancia))


def interpretar(argumento: str) -> tuple[str, float | None, str | None]:
    """Lo mismo que /venta, pero que el error no te mande a apuntar una."""
    try:
        coin_id, cantidad, precio = interpretar_venta(argumento)
        if precio:
            cobrado(precio, 1)
    except MovimientoError:
        raise MovimientoError(f"Escríbelo así: {EJEMPLO}") from None
    return coin_id, cantidad, precio


def calcular(
    antes: Posicion,
    vendido: float,
    dinero: float,
    queda: Posicion | None,
    este_año: Impuestos,
) -> Simulacion:
    return Simulacion(
        antes.coin_id,
        vendido,
        dinero,
        ganancias.coste_de(antes, vendido),
        queda.cantidad if queda else 0,
        este_año.ganancia,
        este_año.sin_datos,
    )
