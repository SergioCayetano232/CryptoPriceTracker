"""/sesgo: con qué humor del mercado compras y vendes, y cómo te ha ido."""

from dataclasses import dataclass
from datetime import date

from ..miedo import Indice
from .movimientos import Movimiento

# Las cinco de alternative.me, de pánico a euforia.
CLASES = ("extreme fear", "fear", "neutral", "greed", "extreme greed")

# Su propio corte: hasta 45 es miedo y desde 55, codicia.
MIEDO = 45
CODICIA = 55
# Con menos, decir "sueles" es pasarse.
MINIMO = 3


@dataclass(frozen=True)
class Grupo:
    clase: str
    veces: int
    cambio: float | None  # lo que van esas compras hasta hoy, en %; None sin coste


@dataclass(frozen=True)
class Lado:
    veces: int
    media: float  # el índice medio de esos días
    grupos: list[Grupo]  # solo las clases que tienen alguno, de miedo a codicia

    @property
    def humor(self) -> str | None:
        """'miedo', 'codicia', 'neutral', o None si son muy pocas."""
        if self.veces < MINIMO:
            return None
        if self.media <= MIEDO:
            return "miedo"
        if self.media >= CODICIA:
            return "codicia"
        return "neutral"


@dataclass(frozen=True)
class Sesgo:
    compras: Lado | None
    ventas: Lado | None
    sin_indice: int  # movimientos de días que el índice no tiene


def dias_hacia_atras(movimientos: list[Movimiento], hoy: date) -> int:
    """Lo que hay que pedirle a alternative.me para llegar al primero."""
    primero = min(m.cuando.date() for m in movimientos)
    return (hoy - primero).days + 2


def calcular(
    movimientos: list[Movimiento],
    indices: list[Indice],
    precios: dict[str, float],
) -> Sesgo:
    # El índice sale una vez al día en UTC, y las fechas se guardan en UTC.
    por_dia = {i.dia: i for i in indices}
    compras, ventas, sin_indice = [], [], 0
    for m in movimientos:
        indice = por_dia.get(m.cuando.date())
        if indice is None:
            sin_indice += 1
            continue
        (compras if m.tipo == "compra" else ventas).append((m, indice))
    return Sesgo(_lado(compras, precios), _lado(ventas, None), sin_indice)


def _lado(
    lista: list[tuple[Movimiento, Indice]], precios: dict[str, float] | None
) -> Lado | None:
    if not lista:
        return None
    grupos = []
    for clase in CLASES:
        suyos = [m for m, i in lista if i.clase.lower() == clase]
        if suyos:
            grupos.append(Grupo(clase, len(suyos), _cambio(suyos, precios)))
    media = sum(i.valor for _, i in lista) / len(lista)
    return Lado(len(lista), media, grupos)


def _cambio(suyos: list[Movimiento], precios: dict[str, float] | None) -> float | None:
    """Lo que valen hoy contra lo que costaron, todas juntas."""
    if precios is None:
        return None
    # Las que no llevan coste o no tienen precio de hoy, fuera; no a cero.
    validas = [m for m in suyos if m.coste and m.coin_id in precios]
    if not validas:
        return None
    costo = sum(m.coste for m in validas)
    vale = sum(m.cantidad * precios[m.coin_id] for m in validas)
    return (vale / costo - 1) * 100
