"""/compras: tu mejor y tu peor compra, y cuántas van ganando."""

from dataclasses import dataclass

from .movimientos import Movimiento


@dataclass(frozen=True)
class Compra:
    movimiento: Movimiento
    precio: float  # el de ahora

    @property
    def pagado(self) -> float:
        return self.movimiento.coste / self.movimiento.cantidad

    @property
    def cambio(self) -> float:
        return (self.precio / self.pagado - 1) * 100

    @property
    def ganancia(self) -> float:
        # Como si no la hubieras vendido: lo que mide es si compraste bien.
        return self.movimiento.cantidad * self.precio - self.movimiento.coste


@dataclass(frozen=True)
class Resumen:
    mejor: Compra
    peor: Compra
    verdes: int
    rojas: int
    sin_precio: int  # apuntadas sin lo que costaron, o sin precio de hoy

    @property
    def total(self) -> int:
        return self.verdes + self.rojas


def calcular(lista: list[Movimiento], precios: dict[str, float]) -> Resumen | None:
    """None si no hay ninguna compra que se pueda comparar."""
    todas = [m for m in lista if m.tipo == "compra"]
    contables = [
        Compra(m, precios[m.coin_id])
        for m in todas
        if m.coste and m.cantidad > 0 and m.coin_id in precios
    ]
    if not contables:
        return None

    # Con empate, la más vieja: es la que antes acertaste.
    por_cambio = sorted(contables, key=lambda c: (-c.cambio, c.movimiento.id))
    verdes = sum(1 for c in contables if c.cambio >= 0)
    return Resumen(
        mejor=por_cambio[0],
        peor=por_cambio[-1],
        verdes=verdes,
        rojas=len(contables) - verdes,
        sin_precio=len(todas) - len(contables),
    )
