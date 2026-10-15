"""/diasemana: qué día de la semana suele subir más y cuál bajar."""

from dataclasses import dataclass
from datetime import date

from .periodo import PeriodoError, es_tramo, leer
from .simbolos import a_id

POR_DEFECTO = 90 * 24

EJEMPLO = "/diasemana bitcoin 90d"

NOMBRES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


@dataclass(frozen=True)
class Dia:
    nombre: str
    media: float  # lo que cambia de media ese día, en %
    veces: int


@dataclass(frozen=True)
class DiasSemana:
    dias: list[Dia]  # solo los que tienen algún dato, de lunes a domingo
    desde: date

    @property
    def mejor(self) -> Dia:
        return max(self.dias, key=lambda d: d.media)

    @property
    def peor(self) -> Dia:
        return min(self.dias, key=lambda d: d.media)


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 30d' -> ('bitcoin', 720). Sin tramo, 90 días; sin cripto, ''."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if len(partes) > 1:
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")
    return (a_id(partes[0]) if partes else ""), horas


def calcular(dias: list[tuple[date, float]]) -> DiasSemana | None:
    """dias es el último precio de cada día (sale de por_dias). None si no hay
    ni un día comparado con el anterior."""
    cambios: list[list[float]] = [[] for _ in NOMBRES]
    desde = None
    for (ayer, anterior), (dia, precio) in zip(dias, dias[1:], strict=False):
        if anterior <= 0 or (dia - ayer).days != 1:
            continue
        if desde is None:
            desde = ayer
        cambios[dia.weekday()].append((precio / anterior - 1) * 100)

    if desde is None:
        return None
    por_dia = zip(NOMBRES, cambios, strict=True)
    return DiasSemana([Dia(n, sum(c) / len(c), len(c)) for n, c in por_dia if c], desde)
