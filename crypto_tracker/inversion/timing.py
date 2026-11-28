"""/timing: si aciertas el momento o daría igual comprar un día cualquiera."""

from dataclasses import dataclass
from datetime import date, datetime

from ..indicadores.volatilidad import por_dias
from .movimientos import Movimiento

# Los días de antes y de después con los que comparo cada compra.
VENTANA = 15
# Con menos días alrededor, la media no es "un día cualquiera".
MINIMO_DIAS = 10
# Lo que da CoinGecko gratis hacia atrás.
MAXIMO_DIAS = 365
# Por debajo de esto, comprar con ojo o al azar es lo mismo.
EMPATE = 2.0


@dataclass(frozen=True)
class Compra:
    movimiento: Movimiento
    media: float  # la de los días de alrededor
    suelo: float
    techo: float

    @property
    def pagado(self) -> float:
        return self.movimiento.coste / self.movimiento.cantidad

    @property
    def ahorro(self) -> float:
        """Cuánto menos pagaste que la media, en %. Negativo si pagaste más."""
        return (1 - self.pagado / self.media) * 100

    @property
    def posicion(self) -> float | None:
        """0 si compraste en el día más barato de alrededor, 100 en el más caro."""
        if self.techo <= self.suelo:
            return None
        # Con la comisión puedes salir por encima del techo; lo dejo en 100.
        return min(
            100.0,
            max(0.0, (self.pagado - self.suelo) / (self.techo - self.suelo) * 100),
        )


@dataclass(frozen=True)
class Timing:
    compras: list[Compra]
    fuera: int  # sin coste o sin precios de alrededor
    ventana: int = VENTANA

    @property
    def ahorro(self) -> float:
        """Todo junto, pesando más las compras grandes."""
        coste = sum(c.movimiento.coste for c in self.compras)
        a_la_media = sum(c.movimiento.cantidad * c.media for c in self.compras)
        return (1 - coste / a_la_media) * 100

    @property
    def baratas(self) -> int:
        return sum(c.ahorro > 0 for c in self.compras)

    @property
    def posicion(self) -> float | None:
        lista = [c.posicion for c in self.compras if c.posicion is not None]
        return sum(lista) / len(lista) if lista else None

    @property
    def mejor(self) -> Compra:
        return max(self.compras, key=lambda c: c.ahorro)

    @property
    def peor(self) -> Compra:
        return min(self.compras, key=lambda c: c.ahorro)

    @property
    def veredicto(self) -> str:
        if self.ahorro >= EMPATE:
            return "ojo"
        if self.ahorro <= -EMPATE:
            return "caro"
        return "azar"


def a_mirar(movimientos: list[Movimiento]) -> list[Movimiento]:
    return [m for m in movimientos if m.tipo == "compra"]


def dias_a_pedir(compras: list[Movimiento], hoy: date) -> int:
    primero = min(m.cuando.date() for m in compras)
    return min(MAXIMO_DIAS, (hoy - primero).days + VENTANA + 1)


def evaluar(m: Movimiento, diarios: dict[date, float]) -> Compra | None:
    if not m.coste or not m.cantidad:
        return None
    dia = m.cuando.astimezone().date()
    alrededor = [
        p for d, p in diarios.items() if abs((d - dia).days) <= VENTANA and d != dia
    ]
    if len(alrededor) < MINIMO_DIAS:
        return None
    return Compra(m, sum(alrededor) / len(alrededor), min(alrededor), max(alrededor))


def calcular(
    compras: list[Movimiento], series: dict[str, list[tuple[datetime, float]]]
) -> Timing | None:
    """None si ninguna compra se puede comparar."""
    diarios = {c: dict(por_dias(s)) for c, s in series.items()}
    hechas = []
    for m in compras:
        c = evaluar(m, diarios.get(m.coin_id, {}))
        if c is not None:
            hechas.append(c)
    if not hechas:
        return None
    return Timing(hechas, len(compras) - len(hechas))
