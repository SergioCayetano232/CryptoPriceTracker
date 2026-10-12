"""/objetivo: cuánto valdría tu cartera si una cripto llega a un precio."""

from dataclasses import dataclass

from .cartera import Valor, total
from .puntuales import numero
from .simbolos import a_id

EJEMPLO = "/objetivo bitcoin 100000"


class ObjetivoError(Exception):
    """Lo que escribiste en /objetivo no se entiende."""


@dataclass(frozen=True)
class Escenario:
    coin_id: str
    cantidad: float
    precio: float
    objetivo: float
    ahora: float  # lo que vale toda la cartera hoy
    invertido: float | None = None

    @property
    def despues(self) -> float:
        # Solo se mueve esa cripto; las demás se quedan a su precio de hoy.
        return self.ahora + self.cantidad * (self.objetivo - self.precio)

    @property
    def cambio(self) -> float:
        return (self.objetivo / self.precio - 1) * 100


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 100000' -> ('bitcoin', 100000.0). Vale 100k y 100.000 €."""
    partes = [p for p in argumento.lower().split() if p not in {"€", "$", "£"}]
    if len(partes) != 2:
        raise ObjetivoError(f"Escríbelo así: {EJEMPLO}")

    precio = numero(partes[1])
    if precio is None or precio <= 0:
        raise ObjetivoError(f"'{partes[1]}' no es un precio. Ej: {EJEMPLO}")
    return a_id(partes[0]), precio


def calcular(valores: list[Valor], coin_id: str, objetivo: float) -> Escenario | None:
    """None si esa cripto no está en la cartera."""
    suya = next((v for v in valores if v.coin_id == coin_id), None)
    if suya is None or not suya.cantidad:
        return None
    todo = total(valores)
    return Escenario(
        coin_id, suya.cantidad, suya.precio, objetivo, todo.valor, todo.invertido
    )
