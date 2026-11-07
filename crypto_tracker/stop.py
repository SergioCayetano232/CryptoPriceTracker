"""/stop: avisa al perder o ganar un % sobre lo que te costó, no sobre lo de ahora."""

from dataclasses import dataclass

from .cartera import Valor
from .puntuales import CARTERA, numero
from .simbolos import a_id

EJEMPLO = "/stop eth -15%"


class StopError(Exception):
    """Lo que escribiste en /stop no se entiende o no se puede calcular."""


@dataclass(frozen=True)
class Stop:
    coin_id: str
    porcentaje: float
    coste: float  # el precio medio; en la cartera, todo lo que metiste
    ahora: float  # el precio; en la cartera, lo que vale

    @property
    def objetivo(self) -> float:
        return self.coste * (1 + self.porcentaje / 100)

    @property
    def sube(self) -> bool:
        return self.porcentaje > 0

    @property
    def llevas(self) -> float:
        return (self.ahora / self.coste - 1) * 100

    @property
    def ya_llego(self) -> bool:
        if self.sube:
            return self.ahora >= self.objetivo
        return self.ahora <= self.objetivo

    @property
    def nota(self) -> str:
        """Lo que sale en /alertas y en el aviso, para que no parezca una normal."""
        pct = f"{self.porcentaje:+g}".replace(".", ",")
        return f"Stop: {pct}% sobre lo que te costó"


def interpretar(argumento: str) -> tuple[str, float]:
    """'eth -15%' -> ('ethereum', -15.0)."""
    partes = argumento.split()
    if len(partes) != 2 or not partes[1].endswith("%"):
        raise StopError(f"Escríbelo así: {EJEMPLO}")

    texto = partes[1][:-1]
    # Aquí no hay "desde ahora" que valga: sin signo no sé si es pérdida o ganancia.
    if not texto.startswith(("+", "-")):
        raise StopError(f"¿Perder o ganar? Pon -{texto}% o +{texto}%")

    porcentaje = numero(texto[1:])
    if porcentaje is None or porcentaje <= 0:
        raise StopError(f"'{partes[1]}' no es un porcentaje. Ej: {EJEMPLO}")
    if texto.startswith("-"):
        porcentaje = -porcentaje
    if porcentaje <= -100:
        raise StopError("No puedes perder un 100 % o más, se quedaría en nada.")

    return a_id(partes[0]), porcentaje


def calcular(coin_id: str, porcentaje: float, valor: Valor) -> Stop:
    if coin_id == CARTERA:
        coste, ahora = valor.invertido, valor.valor
        falta = "Para eso necesito lo que te costó cada una de tu cartera"
    else:
        coste, ahora = valor.precio_medio, valor.precio
        falta = "Para eso necesito lo que te costó"
    if not coste or ahora is None:
        raise StopError(f"{falta}. Apúntalo así: /compra bitcoin 0.01 600")
    return Stop(coin_id, porcentaje, coste, ahora)
