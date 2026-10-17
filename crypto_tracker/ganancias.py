"""Lo que has ganado o perdido de verdad, con lo que ya has vendido."""

from dataclasses import dataclass

from .config import Posicion
from .movimientos import Movimiento


@dataclass(frozen=True)
class Ganancias:
    por_cripto: list[tuple[str, float]]  # la que mas ha dado primero
    total: float
    # Las de antes de apuntar a cuanto vendias, o de algo que no sabes lo que costo
    sin_datos: int


def de_venta(
    antes: Posicion | None, vendido: float, cobrado: float | None
) -> float | None:
    """Lo cobrado menos lo que costo esa parte. None si falta alguna de las dos."""
    if cobrado is None or antes is None or antes.invertido is None:
        return None
    # Al precio medio, igual que /vender baja lo invertido en proporcion.
    return cobrado - antes.invertido * vendido / antes.cantidad


def calcular(ventas: list[Movimiento]) -> Ganancias:
    por_cripto: dict[str, float] = {}
    sin_datos = 0
    for v in ventas:
        ganancia = de_venta(v.antes, v.cantidad, v.coste)
        if ganancia is None:
            sin_datos += 1
            continue
        por_cripto[v.coin_id] = por_cripto.get(v.coin_id, 0) + ganancia

    ordenadas = sorted(por_cripto.items(), key=lambda x: x[1], reverse=True)
    return Ganancias(ordenadas, sum(por_cripto.values()), sin_datos)
