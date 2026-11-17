"""/escalera: vender por tramos al subir, en vez de todo de golpe."""

from dataclasses import dataclass

from . import fifo
from .config import Posicion
from .impuestos import cuota
from .movimientos import Movimiento
from .puntuales import numero
from .simbolos import a_id

EJEMPLO = "/escalera btc 80000 90000 100000"
MINIMO, MAXIMO = 2, 10


class EscaleraError(Exception):
    """Lo que escribiste en /escalera no se entiende o no se puede hacer."""


@dataclass(frozen=True)
class Escalon:
    precio: float
    cantidad: float
    coste: float | None  # None si no sé lo que te costó lo que vendes aquí
    hacienda: float | None  # lo que sube la cuenta del año con este escalón

    @property
    def cobrado(self) -> float:
        return self.precio * self.cantidad

    @property
    def ganancia(self) -> float | None:
        return None if self.coste is None else self.cobrado - self.coste


@dataclass(frozen=True)
class Escalera:
    coin_id: str
    porcentaje: float  # qué parte de lo que tienes vendes entre todos
    escalones: list[Escalon]
    queda: float

    @property
    def vendido(self) -> float:
        return sum(e.cantidad for e in self.escalones)

    @property
    def cobrado(self) -> float:
        return sum(e.cobrado for e in self.escalones)

    @property
    def ganancia(self) -> float | None:
        if any(e.ganancia is None for e in self.escalones):
            return None
        return sum(e.ganancia for e in self.escalones)

    @property
    def hacienda(self) -> float | None:
        if any(e.hacienda is None for e in self.escalones):
            return None
        return sum(e.hacienda for e in self.escalones)


def interpretar(argumento: str) -> tuple[str, list[float], float]:
    """'btc 80k 90k 100k 50%' -> ('bitcoin', [80000, 90000, 100000], 50.0)."""
    partes = argumento.split()
    if len(partes) < 1 + MINIMO:
        raise EscaleraError(f"Pon la cripto y al menos dos precios: {EJEMPLO}")

    porcentaje = 100.0
    if partes[-1].endswith("%"):
        leido = numero(partes[-1][:-1])
        if leido is None or not 0 < leido <= 100:
            raise EscaleraError(
                f"'{partes[-1]}' no vale: es qué parte vendes, entre 1% y 100%."
            )
        porcentaje = leido
        partes = partes[:-1]

    precios = []
    for texto in partes[1:]:
        precio = numero(texto)
        if precio is None or precio <= 0:
            raise EscaleraError(f"'{texto}' no es un precio. Ej: {EJEMPLO}")
        precios.append(precio)

    precios = sorted(set(precios))
    if len(precios) < MINIMO:
        raise EscaleraError(f"Hacen falta al menos dos precios distintos: {EJEMPLO}")
    if len(precios) > MAXIMO:
        raise EscaleraError(f"Como mucho {MAXIMO} escalones, que si no es un goteo.")
    return a_id(partes[0]), precios, porcentaje


def calcular(
    antes: Posicion,
    precios: list[float],
    porcentaje: float,
    ahora: float,
    ya_ganado: float,
    historia: list[Movimiento] | tuple = (),
) -> Escalera:
    """ya_ganado es lo de este año antes de vender nada, para el tramo de Hacienda."""
    if precios[0] <= ahora:
        raise EscaleraError(
            "El primer escalón tiene que estar por encima del precio de ahora. "
            "Si ya está ahí, eso es vender, no una escalera."
        )

    total = antes.cantidad * porcentaje / 100
    parte = total / len(precios)
    escalones = []
    vendido = 0.0
    coste_antes: float | None = 0.0
    ganado = ya_ganado
    for precio in precios:
        vendido += parte
        # FIFO sobre lo acumulado: cada escalón vende lo que deja el anterior.
        coste_hasta = fifo.coste_de_vender(list(historia), antes, vendido)
        coste = None
        if coste_hasta is not None and coste_antes is not None:
            coste = coste_hasta - coste_antes
        coste_antes = coste_hasta

        hacienda = None
        if coste is not None:
            ganancia = precio * parte - coste
            hacienda = cuota(ganado + ganancia) - cuota(ganado)
            ganado += ganancia
        escalones.append(Escalon(precio, parte, coste, hacienda))

    return Escalera(antes.coin_id, porcentaje, escalones, antes.cantidad - total)


def nota(numero: int, de: int, cantidad: str) -> str:
    """Lo que sale en /alertas y en el aviso de cada escalón."""
    return f"Escalera {numero}/{de}: vende {cantidad}"
