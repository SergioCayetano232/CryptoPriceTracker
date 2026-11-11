"""/promediar: cuánto comprar hoy para bajar tu precio medio a una cifra."""

from dataclasses import dataclass

from .cartera import Valor
from .puntuales import numero
from .simbolos import a_id

EJEMPLO = "/promediar bitcoin 50000"


class PromediarError(Exception):
    """Lo que escribiste en /promediar no se entiende."""


@dataclass(frozen=True)
class Promedio:
    coin_id: str
    cantidad: float  # la que tienes
    medio: float  # a cuánto te salió
    precio: float  # el de ahora
    objetivo: float  # el medio que quieres

    @property
    def ya_esta(self) -> bool:
        return self.medio <= self.objetivo

    @property
    def imposible(self) -> bool:
        # Comprando a un precio, el medio se acerca a él pero nunca lo cruza.
        return not self.ya_esta and self.objetivo <= self.precio

    @property
    def comprar(self) -> float | None:
        """Lo que hay que comprar al precio de hoy. None si no tiene sentido."""
        if self.ya_esta or self.imposible:
            return None
        return (
            self.cantidad * (self.medio - self.objetivo) / (self.objetivo - self.precio)
        )

    @property
    def dinero(self) -> float | None:
        return None if self.comprar is None else self.comprar * self.precio


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 50000' -> ('bitcoin', 50000.0). Vale 50k y 50.000 €."""
    partes = [p for p in argumento.lower().split() if p not in {"€", "$", "£"}]
    if len(partes) != 2:
        raise PromediarError(f"Escríbelo así: {EJEMPLO}")

    precio = numero(partes[1])
    if precio is None or precio <= 0:
        raise PromediarError(f"'{partes[1]}' no es un precio. Ej: {EJEMPLO}")
    return a_id(partes[0]), precio


def calcular(valor: Valor, objetivo: float) -> Promedio | None:
    """None si no sé lo que te costó."""
    if valor.precio_medio is None or not valor.precio:
        return None
    return Promedio(
        valor.coin_id, valor.cantidad, valor.precio_medio, valor.precio, objetivo
    )
