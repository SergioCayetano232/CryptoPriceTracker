"""/oro: tu cartera en gramos de oro."""

from dataclasses import dataclass

# Saco el precio de PAX Gold, que es una onza por token. Así no hace falta
# otra API solo para el oro.
COIN_ID = "pax-gold"
GRAMOS_ONZA = 31.1035


@dataclass(frozen=True)
class Oro:
    valor: float  # lo que vale tu cartera
    onza: float  # lo que vale una onza de oro

    @property
    def gramo(self) -> float:
        return self.onza / GRAMOS_ONZA

    @property
    def gramos(self) -> float:
        return self.valor / self.gramo

    @property
    def onzas(self) -> float:
        return self.valor / self.onza
