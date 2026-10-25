"""/millonario: cuánto de una cripto hace falta para tener un millón."""

from dataclasses import dataclass

MILLON = 1_000_000


@dataclass(frozen=True)
class Millonario:
    precio: float
    tienes: float | None = None  # lo de tu cartera, si la tienes en ella

    @property
    def necesitas(self) -> float:
        return MILLON / self.precio

    @property
    def hecho(self) -> float | None:
        """% del camino que ya llevas con lo de tu cartera."""
        if not self.tienes:
            return None
        return self.tienes / self.necesitas * 100


def cantidad(valor: float) -> str:
    """12,1641 BTC o 45.871.560 SHIB: con decimales solo si son pocas."""
    if valor >= 1000:
        return f"{valor:,.0f}".replace(",", ".")
    texto = f"{valor:.4f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")
