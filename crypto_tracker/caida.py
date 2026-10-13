"""/caida: cuánto ha bajado desde el máximo y la peor caída del tramo."""

from dataclasses import dataclass
from datetime import datetime

from .periodo import PeriodoError, es_tramo, leer
from .simbolos import a_id

POR_DEFECTO = 30 * 24

EJEMPLO = "/caida bitcoin 30d"


@dataclass(frozen=True)
class Caida:
    maximo: float
    cuando_maximo: datetime
    ahora: float
    # La peor bajada de un pico a un valle posterior, aunque luego recuperara.
    pico: float
    cuando_pico: datetime
    valle: float
    cuando_valle: datetime

    @property
    def desde_maximo(self) -> float:
        return (self.ahora / self.maximo - 1) * 100

    @property
    def peor(self) -> float:
        return (self.valle / self.pico - 1) * 100


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 7d' -> ('bitcoin', 168). Sin tramo, 30 días; sin cripto, ''."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if len(partes) > 1:
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")
    return (a_id(partes[0]) if partes else ""), horas


def calcular(serie: list[tuple[datetime, float]]) -> Caida | None:
    """serie va del más viejo al más nuevo. None si no hay ni dos precios."""
    if len(serie) < 2:
        return None

    alto = serie[0]
    pico, valle = serie[0], serie[0]
    for fila in serie[1:]:
        # >= para quedarme con el máximo más reciente si se repite
        if fila[1] >= alto[1]:
            alto = fila
        elif fila[1] / alto[1] < valle[1] / pico[1]:
            pico, valle = alto, fila

    return Caida(alto[1], alto[0], serie[-1][1], pico[1], pico[0], valle[1], valle[0])
