"""/dominancia: si el dinero se va a las altcoins o vuelve a bitcoin."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .mercado import Mercado

TRAMOS = (1, 7, 30)
HORAS = (max(TRAMOS) + 5) * 24

# Menos de un punto en una semana es lo que baila cualquier semana.
PUNTOS = 1.0


@dataclass(frozen=True)
class Foto:
    cuando: datetime
    bitcoin: float  # % del total
    ethereum: float | None
    estables: float | None


@dataclass(frozen=True)
class Dominancia:
    ahora: Mercado
    cambios: list[tuple[int, float]]  # (días, puntos que ha ganado o perdido bitcoin)

    @property
    def hacia(self) -> str | None:
        """'bitcoin', 'altcoins', '' si está quieta o None si no hay una semana."""
        # Lo más largo que haya: 30 días dicen más que 7.
        largos = [p for d, p in self.cambios if d >= 7]
        if not largos:
            return None
        if largos[-1] >= PUNTOS:
            return "bitcoin"
        return "altcoins" if largos[-1] <= -PUNTOS else ""


def toca_guardar(ultima: datetime | None, ahora: datetime) -> bool:
    """Una foto al día, que más gastaría consultas para nada."""
    return ultima is None or ultima.astimezone().date() < ahora.astimezone().date()


def hace(fotos: list[Foto], ahora: datetime, dias: int) -> Foto | None:
    """La guardada más cerca de hace esos días, si no está muy lejos."""
    objetivo = ahora - timedelta(days=dias)
    # Se guarda una al día a la hora que sea: la de ayer puede ser de hace 30 h.
    margen = timedelta(days=max(0.75, dias * 0.1))
    cerca = [f for f in fotos if abs(f.cuando - objetivo) <= margen]
    return min(cerca, key=lambda f: abs(f.cuando - objetivo), default=None)


def calcular(ahora: Mercado, fotos: list[Foto], cuando: datetime) -> Dominancia:
    cambios = []
    for dias in TRAMOS:
        antes = hace(fotos, cuando, dias)
        if antes is not None:
            cambios.append((dias, ahora.bitcoin - antes.bitcoin))
    return Dominancia(ahora, cambios)
