"""/sat: lo que vale un satoshi y cuántos te dan unos pocos euros."""

from dataclasses import dataclass

SATS_POR_BTC = 100_000_000

CANTIDADES = (1, 10, 100)


@dataclass(frozen=True)
class Sat:
    bitcoin: float  # el precio de un bitcoin

    @property
    def valor(self) -> float:
        return self.bitcoin / SATS_POR_BTC

    def por(self, dinero: float) -> int:
        """Cuántos sats compras con eso."""
        return round(dinero / self.valor)
