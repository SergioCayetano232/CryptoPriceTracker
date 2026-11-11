"""/posicion: cuánto meter para no perder más de un % si salta el stop."""

from dataclasses import dataclass

from .puntuales import numero
from .simbolos import a_id

EJEMPLO = "/posicion 1000 2% -10%"


class PosicionError(Exception):
    """Lo que escribiste en /posicion no se entiende."""


@dataclass(frozen=True)
class Peticion:
    capital: float
    riesgo: float  # el % de lo que tienes que aceptas perder
    stop: float | None = None  # a cuánto por debajo, en %
    stop_precio: float | None = None  # o el precio del stop, con cripto
    coin_id: str | None = None


@dataclass(frozen=True)
class Entrada:
    capital: float
    riesgo: float
    stop: float  # en %, siempre en positivo
    precio: float | None = None
    coin_id: str | None = None

    @property
    def todo(self) -> bool:
        """Con el stop tan cerca, ni metiéndolo todo se llega a ese riesgo."""
        return self.capital * self.riesgo / self.stop >= self.capital

    @property
    def dinero(self) -> float:
        return min(self.capital * self.riesgo / self.stop, self.capital)

    @property
    def perdida(self) -> float:
        return self.dinero * self.stop / 100

    @property
    def cantidad(self) -> float | None:
        return None if not self.precio else self.dinero / self.precio

    @property
    def precio_stop(self) -> float | None:
        return None if not self.precio else self.precio * (1 - self.stop / 100)


def _porcentaje(texto: str) -> float | None:
    if not texto.endswith("%"):
        return None
    return numero(texto[:-1].lstrip("+-"))


def interpretar(argumento: str) -> Peticion:
    """'1000 2% -10%' o 'btc 1000 2% 58000'. La palabra stop se puede poner o no."""
    partes = [p for p in argumento.lower().split() if p not in {"stop", "€", "$", "£"}]
    coin_id = None
    if len(partes) == 4:
        coin_id = a_id(partes.pop(0))
    if len(partes) != 3:
        raise PosicionError(
            f"Escríbelo así: {EJEMPLO} (lo que tienes, lo que aceptas perder y "
            "dónde pones el stop). Con la cripto delante, el stop puede ser un "
            "precio: /posicion btc 1000 2% 58000"
        )

    capital = numero(partes[0])
    if capital is None or capital <= 0:
        raise PosicionError(f"'{partes[0]}' no es una cantidad. Ej: {EJEMPLO}")

    riesgo = _porcentaje(partes[1])
    if riesgo is None or not 0 < riesgo <= 100:
        raise PosicionError(
            f"Lo que aceptas perder va en %, entre 0 y 100: 2%. Ej: {EJEMPLO}"
        )

    stop = _porcentaje(partes[2])
    if stop is not None:
        if not 0 < stop < 100:
            raise PosicionError(f"El stop va entre 0% y 100%: -10%. Ej: {EJEMPLO}")
        return Peticion(capital, riesgo, stop=stop, coin_id=coin_id)

    precio = numero(partes[2])
    if precio is None or precio <= 0:
        raise PosicionError(f"'{partes[2]}' no es un stop. Ej: {EJEMPLO}")
    if coin_id is None:
        raise PosicionError(
            "Para poner el stop como precio, dime de qué cripto: "
            "/posicion btc 1000 2% 58000"
        )
    return Peticion(capital, riesgo, stop_precio=precio, coin_id=coin_id)


def calcular(p: Peticion, precio: float | None = None) -> Entrada:
    stop = p.stop
    if p.stop_precio is not None:
        if precio is None or p.stop_precio >= precio:
            raise PosicionError(
                "El stop tiene que estar por debajo del precio de ahora."
            )
        stop = (1 - p.stop_precio / precio) * 100
    return Entrada(p.capital, p.riesgo, stop, precio, p.coin_id)
