"""/ultimo: cuándo saltó el último aviso de cada cripto."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Aviso:
    cuando: datetime
    precio: float  # al que estaba al avisar
    sube: bool


@dataclass(frozen=True)
class Ultimo:
    coin_id: str
    aviso: Aviso | None  # None si aún no ha avisado nunca
    ahora: float | None = None  # último precio guardado

    @property
    def desde_entonces(self) -> float | None:
        if self.aviso is None or not self.ahora:
            return None
        return (self.ahora / self.aviso.precio - 1) * 100


def juntar(
    vigiladas: list[str],
    avisos: dict[str, Aviso],
    precios: dict[str, float | None],
) -> list[Ultimo]:
    """Las que vigilas, la que avisó hace menos primero y las que nunca, al final.

    Las que ya no vigilas pero avisaron alguna vez no salen: ya no te importan.
    """
    lista = [Ultimo(c, avisos.get(c), precios.get(c)) for c in vigiladas]
    con = sorted((u for u in lista if u.aviso), key=lambda u: u.aviso.cuando)
    sin = [u for u in lista if u.aviso is None]
    return [*reversed(con), *sin]
