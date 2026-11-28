"""/backtest: vender al subir un % y recomprar al bajar, contra no tocar nada."""

from dataclasses import dataclass
from datetime import datetime

from .avisos.puntuales import numero
from .nucleo.periodo import PeriodoError, es_tramo, leer
from .nucleo.simbolos import a_id

EJEMPLO = "/backtest btc 20% 90d"
POR_DEFECTO = 20.0
HORAS = 90 * 24
# Con 1.000 se lee de un vistazo cuánto es en %.
INICIAL = 1000.0


@dataclass(frozen=True)
class Backtest:
    porcentaje: float
    final: float  # lo que tendrías siguiendo la regla
    hodl: float  # lo que tendrías sin tocar nada
    ventas: int
    compras: int
    dentro: bool  # si ahora mismo tendrías la cripto o estarías en euros
    siguiente: float  # el precio al que tocaría la próxima operación
    desde: datetime

    @property
    def diferencia(self) -> float:
        return self.final - self.hodl

    @property
    def regla(self) -> float:
        return (self.final / INICIAL - 1) * 100

    @property
    def sin_tocar(self) -> float:
        return (self.hodl / INICIAL - 1) * 100


def interpretar(argumento: str) -> tuple[str, float, float]:
    """'btc 15% 30d' -> ('bitcoin', 15, 720). Sin %, el 20; sin tramo, 90 días."""
    partes = argumento.split()
    horas = HORAS
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())

    porcentaje = POR_DEFECTO
    if len(partes) == 2:
        porcentaje = numero(partes.pop().removesuffix("%").removeprefix("+"))
        if porcentaje is None or porcentaje <= 0:
            raise PeriodoError(f"Escríbelo así: {EJEMPLO}")
        # Al 100% recomprar sería esperar a que valga cero.
        if porcentaje >= 100:
            raise PeriodoError("Pon un % menor de 100, como /backtest btc 20%")
    if len(partes) > 1:
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")
    return (a_id(partes[0]) if partes else ""), porcentaje, horas


def calcular(serie: list[tuple[datetime, float]], porcentaje: float) -> Backtest | None:
    """serie va del más viejo al más nuevo. Empieza comprando con el primer precio."""
    if len(serie) < 2:
        return None

    primero = serie[0][1]
    cantidad, euros = INICIAL / primero, 0.0
    # La referencia es el precio de la última operación, no el máximo.
    referencia, dentro = primero, True
    ventas = compras = 0
    for _, precio in serie[1:]:
        if dentro and precio >= referencia * (1 + porcentaje / 100):
            euros, cantidad, dentro = cantidad * precio, 0.0, False
            referencia, ventas = precio, ventas + 1
        elif not dentro and precio <= referencia * (1 - porcentaje / 100):
            cantidad, euros, dentro = euros / precio, 0.0, True
            referencia, compras = precio, compras + 1

    ultimo = serie[-1][1]
    signo = 1 if dentro else -1
    return Backtest(
        porcentaje=porcentaje,
        final=cantidad * ultimo if dentro else euros,
        hodl=INICIAL / primero * ultimo,
        ventas=ventas,
        compras=compras,
        dentro=dentro,
        siguiente=referencia * (1 + signo * porcentaje / 100),
        desde=serie[0][0],
    )
