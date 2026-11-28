"""/juntas: avisa cuando dos criptos que siempre van a la vez dejan de hacerlo.

Suele querer decir que a una le pasa algo que a la otra no: una noticia, un
hackeo, alguien grande vendiendo.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from . import correlacion
from .correlacion import Correlacion
from .nucleo.simbolos import a_id

EJEMPLO = "/juntas btc eth"

# Lo normal se mira en un mes y lo de ahora en diez días: con menos, la
# correlación baila sola de un día para otro.
LARGA = 30
CORTA = 10
HORAS = (LARGA + 1) * 24

# Por debajo de esto en el mes, no van juntas y no hay nada que se pueda romper.
JUNTAS = 0.5
# Lo de ahora por debajo de esto es que se han separado.
ROTA = 0.3
# Y hasta que no vuelvan aquí no se avisa otra vez.
VUELTA = 0.6

QUITAR = frozenset({"no", "quitar", "off"})


class JuntasError(Exception):
    """Lo que escribiste en /juntas no se entiende."""


@dataclass(frozen=True)
class Pareja:
    una: str
    otra: str
    avisada: bool = False


@dataclass(frozen=True)
class Medida:
    corta: Correlacion | None  # la de los últimos CORTA días
    larga: Correlacion | None  # la del mes
    cambio_una: float | None  # lo que se ha movido cada una en CORTA días, en %
    cambio_otra: float | None


def interpretar(argumento: str) -> tuple[str, str, bool]:
    """'btc eth' -> ('bitcoin', 'ethereum', False). Con 'no' al final, True (quitar).

    Siempre en el mismo orden, para que eth btc y btc eth sean la misma pareja.
    """
    partes = argumento.split()
    quitar = len(partes) == 3 and partes[2].lower() in QUITAR
    if len(partes) != 2 and not quitar:
        raise JuntasError(f"De dos en dos. Escríbelo así: {EJEMPLO}")
    una, otra = sorted((a_id(partes[0]), a_id(partes[1])))
    if una == otra:
        raise JuntasError("Son la misma cripto: claro que van juntas")
    return una, otra, quitar


def _ultimos(dias: list[tuple[date, float]], hoy: date, cuantos: int):
    desde = hoy - timedelta(days=cuantos)
    return [(d, p) for d, p in dias if d >= desde]


def _cambio(dias: list[tuple[date, float]]) -> float | None:
    if len(dias) < 2 or not dias[0][1]:
        return None
    return (dias[-1][1] / dias[0][1] - 1) * 100


def medir(
    una: list[tuple[date, float]], otra: list[tuple[date, float]], hoy: date
) -> Medida:
    """Con el precio de cada día de las dos, del más viejo al de hoy."""
    cerca_una = _ultimos(una, hoy, CORTA)
    cerca_otra = _ultimos(otra, hoy, CORTA)
    return Medida(
        correlacion.calcular(cerca_una, cerca_otra),
        correlacion.calcular(_ultimos(una, hoy, LARGA), _ultimos(otra, hoy, LARGA)),
        _cambio(cerca_una),
        _cambio(cerca_otra),
    )


def van_juntas(m: Medida) -> bool | None:
    """Si en el mes van a la vez. None si aún no hay días para saberlo."""
    return None if m.larga is None else m.larga.valor >= JUNTAS


def toca(p: Pareja, m: Medida) -> tuple[bool, bool]:
    """(toca avisar, queda avisada)."""
    if m.corta is None:
        return False, p.avisada
    if p.avisada:
        return False, m.corta.valor < VUELTA
    rota = m.corta.valor <= ROTA
    return rota, rota
