"""/compensar: qué vender en pérdidas para bajar lo que le toca a Hacienda."""

from dataclasses import dataclass

from .fifo import Lote
from .impuestos import Impuestos, cuota
from .movimientos import RESTO

# Por debajo de un céntimo no merece una línea ni una venta.
CENTIMO = 0.01


@dataclass(frozen=True)
class Venta:
    coin_id: str
    cantidad: float
    perdida: float  # en positivo
    precio: float
    todo: bool


@dataclass(frozen=True)
class Compensacion:
    año: int
    ganancia: float
    ventas: list[Venta]
    sin_mirar: list[str]  # les falta el precio o lo que costaron
    sin_datos: int  # ventas de este año que no se pueden contar

    @property
    def compensado(self) -> float:
        return sum(v.perdida for v in self.ventas)

    @property
    def queda(self) -> float:
        return self.ganancia - self.compensado

    @property
    def antes(self) -> float:
        return cuota(self.ganancia)

    @property
    def ahorro(self) -> float:
        return self.antes - cuota(self.queda)


def _perdida(
    lotes: list[Lote], precio: float, objetivo: float = float("inf")
) -> tuple[float, float]:
    """(cuánto vender, cuánto se pierde), sin pasar del objetivo."""
    # No puedes elegir el lote: para llegar a uno en pérdidas hay que vender
    # antes los viejos, aunque esos vayan ganando. Por eso va acumulado.
    acumulado = vendido = 0.0
    mejor = (0.0, 0.0)
    for lote in lotes:
        if lote.coste is None:
            break
        resultado = lote.cantidad * precio - lote.coste
        if resultado < 0 and acumulado + resultado <= -objetivo:
            parte = (-objetivo - acumulado) / resultado
            return vendido + parte * lote.cantidad, objetivo
        acumulado += resultado
        vendido += lote.cantidad
        if -acumulado > mejor[1]:
            mejor = (vendido, -acumulado)
    return mejor


def calcular(
    este_año: Impuestos, lotes: dict[str, list[Lote]], precios: dict[str, float]
) -> Compensacion:
    sin_mirar = [
        coin_id
        for coin_id, suyos in lotes.items()
        if coin_id not in precios or any(lote.coste is None for lote in suyos)
    ]
    maximas = {c: _perdida(lotes[c], p)[1] for c, p in precios.items() if c in lotes}
    # Las que más pierden primero: cuantas menos ventas, menos comisiones.
    orden = sorted(maximas, key=lambda c: maximas[c], reverse=True)

    ventas = []
    falta = max(este_año.ganancia, 0.0)
    for coin_id in orden:
        if falta < CENTIMO or maximas[coin_id] < CENTIMO:
            break
        cantidad, perdida = _perdida(lotes[coin_id], precios[coin_id], falta)
        total = sum(lote.cantidad for lote in lotes[coin_id])
        todo = cantidad >= total - RESTO
        ventas.append(Venta(coin_id, cantidad, perdida, precios[coin_id], todo))
        falta -= perdida

    return Compensacion(
        este_año.año, este_año.ganancia, ventas, sin_mirar, este_año.sin_datos
    )
