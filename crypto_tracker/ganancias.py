"""Lo que has ganado o perdido de verdad, con lo que ya has vendido."""

from dataclasses import dataclass, field

from .config import Posicion
from .movimientos import Movimiento


@dataclass(frozen=True)
class Ganancias:
    por_cripto: list[tuple[str, float]]  # la que mas ha dado primero
    total: float
    # Las de antes de apuntar a cuanto vendias, o de algo que no sabes lo que costo
    sin_datos: int
    # Lo que costó lo vendido de cada una, para sacar el %
    costes: dict[str, float] = field(default_factory=dict)

    def porcentaje(self, coin_id: str) -> float | None:
        coste = self.costes.get(coin_id)
        ganancia = dict(self.por_cripto).get(coin_id)
        if not coste or ganancia is None:
            return None
        return ganancia / coste * 100

    @property
    def porcentaje_total(self) -> float | None:
        coste = sum(self.costes.values())
        return self.total / coste * 100 if coste else None


def de_venta(
    antes: Posicion | None, vendido: float, cobrado: float | None
) -> float | None:
    """Lo cobrado menos lo que costo esa parte. None si falta alguna de las dos."""
    if cobrado is None:
        return None
    coste = coste_de(antes, vendido)
    return None if coste is None else cobrado - coste


def coste_de(antes: Posicion | None, vendido: float) -> float | None:
    """Lo que te costó la parte que vendes."""
    if antes is None or antes.invertido is None:
        return None
    # Al precio medio, igual que /vender baja lo invertido en proporcion.
    return antes.invertido * vendido / antes.cantidad


def calcular(ventas: list[Movimiento]) -> Ganancias:
    por_cripto: dict[str, float] = {}
    costes: dict[str, float] = {}
    sin_datos = 0
    for v in ventas:
        ganancia = de_venta(v.antes, v.cantidad, v.coste)
        if ganancia is None:
            sin_datos += 1
            continue
        por_cripto[v.coin_id] = por_cripto.get(v.coin_id, 0) + ganancia
        costes[v.coin_id] = costes.get(v.coin_id, 0) + coste_de(v.antes, v.cantidad)

    ordenadas = sorted(por_cripto.items(), key=lambda x: x[1], reverse=True)
    return Ganancias(ordenadas, sum(por_cripto.values()), sin_datos, costes)
