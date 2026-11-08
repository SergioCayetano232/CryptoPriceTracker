"""/hodl: cuántos días llevas sin vender cada cripto de la cartera."""

from dataclasses import dataclass
from datetime import date, datetime

from .config import Posicion
from .movimientos import RESTO, Movimiento


@dataclass(frozen=True)
class Hodl:
    coin_id: str
    desde: datetime
    venta: bool  # cuenta desde una venta, no desde la compra
    # Ya la tenías en el .env antes de apuntar nada: llevas más de lo que sale.
    minimo: bool = False

    def dias(self, hoy: date) -> int:
        return (hoy - self.desde.astimezone().date()).days


def _desde(movs: list[Movimiento]) -> Hodl | None:
    """movs van del más viejo al más nuevo, todos de la misma cripto."""
    inicio = 0
    venta = None
    for i, m in enumerate(movs):
        if m.tipo != "venta":
            continue
        quedan = (m.antes.cantidad if m.antes else 0) - m.cantidad
        if quedan <= RESTO:
            # Lo vendiste todo: se empieza a contar en la siguiente compra.
            inicio, venta = i + 1, None
        else:
            venta = m

    if venta is not None:
        return Hodl(venta.coin_id, venta.cuando, True)
    compra = next((m for m in movs[inicio:] if m.tipo != "venta"), None)
    if compra is None:
        return None
    return Hodl(
        compra.coin_id, compra.cuando, False, inicio == 0 and compra.antes is not None
    )


def calcular(
    posiciones: list[Posicion], movimientos: list[Movimiento], hoy: date
) -> tuple[list[Hodl], list[str]]:
    """De la que más lleva a la que menos, y las que no sé desde cuándo tienes."""
    por_cripto: dict[str, list[Movimiento]] = {}
    for m in sorted(movimientos, key=lambda m: m.id):
        por_cripto.setdefault(m.coin_id, []).append(m)

    lista, sin_fecha = [], []
    for p in posiciones:
        if p.cantidad <= RESTO:
            continue
        h = _desde(por_cripto.get(p.coin_id, []))
        if h is None:
            sin_fecha.append(p.coin_id)
        else:
            lista.append(h)
    lista.sort(key=lambda h: h.dias(hoy), reverse=True)
    return lista, sin_fecha
