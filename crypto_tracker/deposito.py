"""/deposito: tu cartera contra haber tenido ese dinero en un depósito."""

from dataclasses import dataclass
from datetime import datetime

from .movimientos import Movimiento
from .puntuales import numero
from .rentabilidad import calcular as rentabilidad
from .rentabilidad import contables

EJEMPLO = "/deposito 3%"

TIPO = 3.0
# Más que esto ya no es un depósito, es una estafa.
MAX_TIPO = 50.0


class DepositoError(Exception):
    """Lo que escribiste en /deposito no se entiende."""


@dataclass(frozen=True)
class Contra:
    real: float  # lo que vale hoy lo que te queda
    deposito: float  # lo que habría en el depósito
    intereses: float  # lo que habría puesto el depósito
    tipo: float  # en %
    desde: datetime
    empate: float | None  # lo que da tu cartera al año, en %
    fuera: int

    @property
    def diferencia(self) -> float:
        return self.real - self.deposito

    @property
    def ventaja(self) -> float | None:
        if self.deposito <= 0:
            return None
        return (self.real / self.deposito - 1) * 100


def interpretar(argumento: str) -> float:
    """'', '3%', '2,5' o 'al 3 %'. Sin nada, TIPO."""
    texto = argumento.lower().replace("al ", "").replace("%", "").strip()
    if not texto:
        return TIPO
    tipo = numero(texto)
    if tipo is None or not 0 < tipo <= MAX_TIPO:
        raise DepositoError(
            f"'{argumento}' no es un interés. Ej: {EJEMPLO} (lo que da al año)"
        )
    return tipo


def calcular(
    lista: list[Movimiento], precios: dict[str, float], ahora: datetime, tipo: float
) -> Contra | None:
    """None si no hay compras con precio o falta el de hoy de alguna."""
    r = rentabilidad(lista, precios, ahora)
    if r is None:
        return None

    dentro, _ = contables(lista)
    saldo = intereses = 0.0
    for m in dentro:
        años = (ahora - m.cuando).total_seconds() / 86400 / 365
        signo = 1 if m.tipo == "compra" else -1
        crece = (1 + tipo / 100) ** años
        saldo += signo * m.coste * crece
        intereses += signo * m.coste * (crece - 1)

    return Contra(
        real=r.vale,
        # Si vendiste por más de lo que tendría, se queda a cero: no te debe nada.
        deposito=max(saldo, 0.0),
        intereses=intereses,
        tipo=tipo,
        desde=min(m.cuando for m in dentro if m.tipo == "compra"),
        empate=r.anual,
        fuera=r.fuera,
    )
