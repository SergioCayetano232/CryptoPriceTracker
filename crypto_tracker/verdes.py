"""/verdes: cuántos días ha subido y cuántos ha bajado en un tramo."""

from dataclasses import dataclass
from datetime import date

from .periodo import PeriodoError, es_tramo, leer
from .simbolos import a_id

POR_DEFECTO = 30 * 24

EJEMPLO = "/verdes bitcoin 30d"

ULTIMOS = 7


@dataclass(frozen=True)
class Verdes:
    suben: int
    bajan: int
    iguales: int
    desde: date
    # De los días seguidos más recientes, el último es el de más a la derecha.
    # True sube, False baja y None igual.
    ultimos: tuple[bool | None, ...] = ()

    @property
    def total(self) -> int:
        return self.suben + self.bajan + self.iguales

    @property
    def porcentaje(self) -> float:
        return self.suben / self.total * 100


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 7d' -> ('bitcoin', 168). Sin tramo, 30 días; sin cripto, ''."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if len(partes) > 1:
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")
    return (a_id(partes[0]) if partes else ""), horas


def calcular(dias: list[tuple[date, float]]) -> Verdes | None:
    """dias es el último precio de cada día (sale de por_dias). None si no hay
    ni un día comparado con el anterior."""
    suben = bajan = iguales = 0
    desde = None
    seguidos: list[bool | None] = []
    for (ayer, anterior), (dia, precio) in zip(dias, dias[1:], strict=False):
        # Con el bot parado no sé cómo fueron esos días, ese salto no cuenta.
        if (dia - ayer).days != 1:
            seguidos = []
            continue
        if desde is None:
            desde = ayer
        if precio > anterior:
            suben += 1
        elif precio < anterior:
            bajan += 1
        else:
            iguales += 1
        seguidos.append(None if precio == anterior else precio > anterior)

    if desde is None:
        return None
    return Verdes(suben, bajan, iguales, desde, tuple(seguidos[-ULTIMOS:]))
