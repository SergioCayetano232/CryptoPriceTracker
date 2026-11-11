"""Aviso de cuando una estable que tienes o vigilas se sale de su dólar."""

from dataclasses import dataclass

ESTABLES = {"tether": "USDT", "usd-coin": "USDC", "dai": "DAI"}

# Un 0,3% arriba o abajo es lo normal en un día movido; un 1% ya no.
LIMITE = 1.0
# Para darla por vuelta tiene que acercarse más, o rondando el 1% avisaría a ratos.
VUELTA = 0.5


@dataclass(frozen=True)
class Desvio:
    coin_id: str
    precio: float  # en dólares

    @property
    def simbolo(self) -> str:
        return ESTABLES[self.coin_id]

    @property
    def porcentaje(self) -> float:
        return (self.precio - 1) * 100


def de_las_tuyas(coin_ids: list[str]) -> list[str]:
    return [c for c in dict.fromkeys(coin_ids) if c in ESTABLES]


def revisar(
    precios_usd: dict[str, float], avisadas: set[str]
) -> tuple[list[Desvio], list[Desvio]]:
    """Las que se acaban de salir y las que han vuelto a su dólar."""
    salen, vuelven = [], []
    for coin_id, precio in precios_usd.items():
        if coin_id not in ESTABLES:
            continue
        d = Desvio(coin_id, precio)
        fuera = abs(d.porcentaje)
        if coin_id not in avisadas and fuera >= LIMITE:
            salen.append(d)
        elif coin_id in avisadas and fuera <= VUELTA:
            vuelven.append(d)
    return salen, vuelven
