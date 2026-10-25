"""/pizza: lo que valdrían hoy los 10.000 BTC que se pagaron por dos pizzas."""

from dataclasses import dataclass
from datetime import date

# Laszlo Hanyecz, el 22 de mayo de 2010. Fue la primera compra con bitcoin.
DIA = date(2010, 5, 22)
BTC = 10_000
PIZZAS = 2


@dataclass(frozen=True)
class Pizza:
    precio: float  # lo que vale un bitcoin ahora
    hoy: date

    @property
    def total(self) -> float:
        return BTC * self.precio

    @property
    def por_pizza(self) -> float:
        return self.total / PIZZAS

    @property
    def aniversario(self) -> int:
        """Días que faltan para el próximo 22 de mayo. 0 si es hoy."""
        este = DIA.replace(year=self.hoy.year)
        if este < self.hoy:
            este = este.replace(year=self.hoy.year + 1)
        return (este - self.hoy).days
