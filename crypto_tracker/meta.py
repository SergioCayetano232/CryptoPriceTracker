"""/meta: cuánto tiene que subir tu cartera para llegar a una cifra."""

from dataclasses import dataclass

from .puntuales import numero

EJEMPLO = "/meta 10000"


class MetaError(Exception):
    """Lo que escribiste en /meta no se entiende."""


@dataclass(frozen=True)
class Meta:
    valor: float  # lo que vale tu cartera hoy
    meta: float

    @property
    def falta(self) -> float:
        return self.meta - self.valor

    @property
    def cambio(self) -> float:
        return (self.meta / self.valor - 1) * 100

    @property
    def veces(self) -> float:
        return self.meta / self.valor

    @property
    def hecho(self) -> float:
        """% del camino, para la barra. Pasada la meta se queda en 100."""
        return min(100.0, self.valor / self.meta * 100)


def interpretar(argumento: str) -> float:
    """'10000', '10k', '10.000 €' -> 10000.0"""
    partes = [p for p in argumento.split() if p not in {"€", "$", "£"}]
    if len(partes) != 1:
        raise MetaError(f"Dime a cuánto quieres llegar. Ej: {EJEMPLO}")
    meta = numero(partes[0])
    if meta is None or meta <= 0:
        raise MetaError(f"'{partes[0]}' no es una cifra. Ej: {EJEMPLO}")
    return meta
