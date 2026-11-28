"""/primera: tu primera compra y lo que ha cambiado el precio desde entonces."""

from dataclasses import dataclass
from datetime import date

from .movimientos import Movimiento


@dataclass(frozen=True)
class Primera:
    compra: Movimiento
    precio: float | None  # el de ahora; None si CoinGecko no responde
    hoy: date

    @property
    def dias(self) -> int:
        return (self.hoy - self.compra.cuando.astimezone().date()).days

    @property
    def pagado(self) -> float | None:
        """A cuánto te salió cada una."""
        if self.compra.coste is None or self.compra.cantidad <= 0:
            return None
        return self.compra.coste / self.compra.cantidad

    @property
    def cambio(self) -> float | None:
        if self.pagado is None or self.precio is None:
            return None
        return (self.precio / self.pagado - 1) * 100


def buscar(movimientos: list[Movimiento]) -> Movimiento | None:
    """La compra más vieja. None si no hay ninguna."""
    compras = [m for m in movimientos if m.tipo == "compra"]
    return min(compras, key=lambda m: m.id, default=None)
