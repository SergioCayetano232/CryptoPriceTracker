"""/extremo: el día que más subió y el que más bajó en un tramo."""

from dataclasses import dataclass
from datetime import date

from .periodo import PeriodoError, es_tramo, leer
from .simbolos import a_id

POR_DEFECTO = 30 * 24

EJEMPLO = "/extremo bitcoin 30d"


@dataclass(frozen=True)
class Dia:
    dia: date
    antes: float  # el cierre del día anterior
    precio: float

    @property
    def cambio(self) -> float:
        return (self.precio / self.antes - 1) * 100


@dataclass(frozen=True)
class Extremo:
    mejor: Dia
    peor: Dia
    dias: int


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 7d' -> ('bitcoin', 168). Sin tramo, 30 días; sin cripto, ''."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if len(partes) > 1:
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")
    return (a_id(partes[0]) if partes else ""), horas


def calcular(dias: list[tuple[date, float]]) -> Extremo | None:
    """dias es el último precio de cada día (sale de por_dias). None si no hay
    ni un día comparado con el anterior."""
    cambios = [
        Dia(dia, anterior, precio)
        for (ayer, anterior), (dia, precio) in zip(dias, dias[1:], strict=False)
        # Con el bot parado, el salto de varios días no es lo que se movió en uno.
        if anterior > 0 and (dia - ayer).days == 1
    ]
    if not cambios:
        return None
    return Extremo(
        max(cambios, key=lambda d: d.cambio),
        min(cambios, key=lambda d: d.cambio),
        len(cambios),
    )
