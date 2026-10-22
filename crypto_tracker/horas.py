"""/horas: a qué hora del día suele estar más barata y a cuál más cara."""

from dataclasses import dataclass
from datetime import date, datetime

from .periodo import PeriodoError, es_tramo, leer
from .simbolos import a_id

POR_DEFECTO = 30 * 24

EJEMPLO = "/horas bitcoin 30d"

# Un día con huecos de horas tiraría la media hacia las que sí tiene.
MINIMO_HORAS = 20


@dataclass(frozen=True)
class Horas:
    medias: dict[int, float]  # hora -> % sobre la media de su día
    dias: int

    @property
    def barata(self) -> int:
        return min(self.medias, key=self.medias.__getitem__)

    @property
    def cara(self) -> int:
        return max(self.medias, key=self.medias.__getitem__)

    @property
    def ahorro(self) -> float:
        """Cuánto más barato sale de media comprar a la barata que a la cara, en %."""
        barata, cara = self.medias[self.barata], self.medias[self.cara]
        return (1 - (1 + barata / 100) / (1 + cara / 100)) * 100


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 7d' -> ('bitcoin', 168). Sin tramo, 30 días; sin cripto, ''."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if len(partes) > 1:
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")
    return (a_id(partes[0]) if partes else ""), horas


def calcular(serie: list[tuple[datetime, float]]) -> Horas | None:
    """None si no hay ni un día con casi todas sus horas."""
    por_dia: dict[date, dict[int, list[float]]] = {}
    for cuando, precio in serie:
        local = cuando.astimezone()
        por_dia.setdefault(local.date(), {}).setdefault(local.hour, []).append(precio)

    # Comparo cada hora con la media de su día: si no, en una subida las
    # últimas horas del tramo saldrían siempre las más caras.
    sumas: dict[int, list[float]] = {}
    dias = 0
    for horas in por_dia.values():
        if len(horas) < MINIMO_HORAS:
            continue
        precios = {h: sum(p) / len(p) for h, p in horas.items()}
        media = sum(precios.values()) / len(precios)
        if media <= 0:
            continue
        dias += 1
        for h, p in precios.items():
            sumas.setdefault(h, []).append((p / media - 1) * 100)

    if not dias:
        return None
    return Horas({h: sum(v) / len(v) for h, v in sorted(sumas.items())}, dias)
