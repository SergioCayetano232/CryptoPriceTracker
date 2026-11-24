"""/longshort: cuántos apuestan a que sube y cuántos a que baja en Binance."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .funding import FundingError, _get

# Todas las cuentas cuentan igual; la de los grandes va por el dinero que mueven.
TODOS_URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
GRANDES_URL = "https://fapi.binance.com/futures/data/topLongShortPositionRatio"
# Binance no guarda más de 30 días de esto.
DIAS = 30

# En bitcoin lo normal ya es un 65-75% a que sube, así que no vale un umbral
# fijo: se compara con su propio mes.
FUERA_DE_LO_NORMAL = 5.0
# Si los pequeños van mucho más a un lado que los grandes, se nota.
SEPARADOS = 10.0

EJEMPLO = "/longshort btc"
EJEMPLO_AVISO = "/longshort btc avisa"

# Binance lo da por días: mirarlo cada cuatro horas ya es de sobra.
CADA = timedelta(hours=4)

ALCISTA, BAJISTA = "alcista", "bajista"


@dataclass(frozen=True)
class Reparto:
    cuando: datetime
    largos: float  # % que apuesta a que sube

    @property
    def cortos(self) -> float:
        return 100 - self.largos


@dataclass(frozen=True)
class LongShort:
    par: str
    todos: list[Reparto]  # del más viejo a hoy
    grandes: Reparto | None  # lo de hoy de los que más mueven, si lo hay

    @property
    def hoy(self) -> Reparto:
        return self.todos[-1]

    @property
    def media(self) -> float:
        return sum(r.largos for r in self.todos) / len(self.todos)

    @property
    def frente_al_mes(self) -> float:
        """Puntos más a la subida que su media del mes (negativo: más a la bajada)."""
        return self.hoy.largos - self.media

    @property
    def separacion(self) -> float | None:
        """Puntos que los pequeños van más a la subida que los grandes."""
        if self.grandes is None:
            return None
        return self.hoy.largos - self.grandes.largos


@dataclass(frozen=True)
class Vigilado:
    """Uno de /longshort btc avisa."""

    par: str
    coin_id: str
    extremo: str = ""  # ALCISTA o BAJISTA si ya se avisó de que está ahí
    mirado: datetime | None = None  # la última vez que se preguntó a Binance


def pedir(par: str) -> tuple[list, list]:
    todos = _get(TODOS_URL, {"symbol": par, "period": "1d", "limit": DIAS})
    # Como en /oi: con un par sin futuros no da error, da la lista vacía.
    if todos == []:
        raise FundingError("sin futuros")
    try:
        grandes = _get(GRANDES_URL, {"symbol": par, "period": "1d", "limit": 1})
    except FundingError:
        grandes = []
    return todos, grandes


def _repartos(datos) -> list[Reparto]:
    lista = []
    for d in datos if isinstance(datos, list) else []:
        if not isinstance(d, dict) or not isinstance(d.get("timestamp"), int):
            continue
        try:
            largos = float(d.get("longAccount")) * 100
        except (TypeError, ValueError):
            continue
        if 0 <= largos <= 100:
            cuando = datetime.fromtimestamp(d["timestamp"] / 1000, timezone.utc)
            lista.append(Reparto(cuando, largos))
    return sorted(lista, key=lambda r: r.cuando)


def leer(par: str, todos, grandes) -> LongShort | None:
    """None si Binance no da ni un día de todas las cuentas."""
    lista = _repartos(todos)
    if not lista:
        return None
    de_grandes = _repartos(grandes)
    return LongShort(par, lista, de_grandes[-1] if de_grandes else None)


def extremo(ls: LongShort) -> str:
    """ALCISTA o BAJISTA si hay más gente de lo normal a un lado; si no, ''."""
    # Con menos de una semana no hay "lo normal" con que comparar.
    if len(ls.todos) < 7:
        return ""
    if ls.frente_al_mes >= FUERA_DE_LO_NORMAL:
        return ALCISTA
    return BAJISTA if ls.frente_al_mes <= -FUERA_DE_LO_NORMAL else ""


def toca_mirar(v: Vigilado, ahora: datetime) -> bool:
    return v.mirado is None or ahora - v.mirado >= CADA


def toca(v: Vigilado, ls: LongShort) -> tuple[bool, str]:
    """(toca avisar, dónde queda). Avisa al entrar en un lado, no mientras sigue."""
    donde = extremo(ls)
    return bool(donde) and donde != v.extremo, donde


def lectura(ls: LongShort) -> tuple[str, str]:
    """(emoji, qué pasa). Primero lo raro del mes, que es lo que más dice."""
    separacion = ls.separacion
    lado = extremo(ls)
    if lado == ALCISTA:
        return "🐂", "Más gente que de costumbre apuesta a que sube"
    if lado == BAJISTA:
        return "🐻", "Más gente que de costumbre apuesta a que baja"
    if separacion is not None and separacion >= SEPARADOS:
        return "🐟", "Los pequeños van más a la subida que los grandes"
    if separacion is not None and separacion <= -SEPARADOS:
        return "🐋", "Los grandes van más a la subida que los pequeños"
    return "😐", "Lo de siempre, ni más ni menos que otros días"
