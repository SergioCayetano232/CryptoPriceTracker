"""/adivina: dices a cuánto crees que está y te digo cuánto te has desviado."""

from dataclasses import dataclass

from .puntuales import numero
from .simbolos import a_id

EJEMPLO = "/adivina 70000 o /adivina eth 2500"

# Hasta qué % de error toca cada nota. Lo que pase del último, "ni de lejos".
NOTAS = (
    (0.5, "🎯", "¡Clavado!"),
    (2, "🔥", "Casi, casi"),
    (5, "🙂", "Caliente"),
    (15, "🤔", "Templado"),
    (40, "🥶", "Frío, frío"),
)
NI_DE_LEJOS = ("🧊", "Ni de lejos")


class AdivinaError(Exception):
    """Lo que escribiste en /adivina no se entiende."""


@dataclass(frozen=True)
class Intento:
    coin_id: str
    dicho: float
    precio: float

    @property
    def error(self) -> float:
        """Cuánto te has desviado, en %. Siempre positivo."""
        return abs(self.dicho / self.precio - 1) * 100

    @property
    def corto(self) -> bool:
        return self.dicho < self.precio

    @property
    def nota(self) -> tuple[str, str]:
        return next(
            ((e, t) for hasta, e, t in NOTAS if self.error <= hasta), NI_DE_LEJOS
        )


def interpretar(argumento: str) -> tuple[str, float]:
    """'70000' -> bitcoin, que es la que todo el mundo sabe. 'eth 2500' -> esa."""
    partes = [p for p in argumento.lower().split() if p not in {"€", "$", "£"}]
    if len(partes) == 1:
        partes = ["bitcoin", partes[0]]
    if len(partes) != 2:
        raise AdivinaError(f"Dime a cuánto crees que está. Ej: {EJEMPLO}")
    dicho = numero(partes[1])
    if dicho is None or dicho <= 0:
        raise AdivinaError(f"'{partes[1]}' no es un precio. Ej: {EJEMPLO}")
    return a_id(partes[0]), dicho
