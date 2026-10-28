"""/mundo: lo que le tocaría a cada persona si se repartieran todos los bitcoin."""

from dataclasses import dataclass

TOTAL = 21_000_000
# La previsión de la ONU para 2026. Redondeo, que tampoco cambia mucho.
PERSONAS = 8_300_000_000
SATS = 100_000_000


@dataclass(frozen=True)
class Mundo:
    precio: float  # lo que vale un bitcoin ahora

    @property
    def btc(self) -> float:
        return TOTAL / PERSONAS

    @property
    def sats(self) -> int:
        return round(self.btc * SATS)

    @property
    def valor(self) -> float:
        return self.btc * self.precio
