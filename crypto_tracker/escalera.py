"""/escalera: vender por tramos al subir, o comprar por tramos al bajar."""

from dataclasses import dataclass

from . import fifo
from .config import Posicion
from .impuestos import cuota
from .movimientos import Movimiento
from .puntuales import numero
from .simbolos import a_id

EJEMPLO = "/escalera btc 80000 90000 100000"
EJEMPLO_COMPRA = "/escalera compra btc 60k 55k 50k con 900"
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


def es_compra(argumento: str) -> bool:
    return argumento.split()[:1] == ["compra"]


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

    return a_id(partes[0]), _precios(partes[1:], EJEMPLO), porcentaje


def _precios(textos: list[str], ejemplo: str) -> list[float]:
    precios = []
    for texto in textos:
        precio = numero(texto)
        if precio is None or precio <= 0:
            raise EscaleraError(f"'{texto}' no es un precio. Ej: {ejemplo}")
        precios.append(precio)

    precios = sorted(set(precios))
    if len(precios) < MINIMO:
        raise EscaleraError(f"Hacen falta al menos dos precios distintos: {ejemplo}")
    if len(precios) > MAXIMO:
        raise EscaleraError(f"Como mucho {MAXIMO} escalones, que si no es un goteo.")
    return precios


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
            "Si ya está ahí, eso es vender, no una escalera.\n"
            f"Si lo que quieres es comprar al bajar: {EJEMPLO_COMPRA}"
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


@dataclass(frozen=True)
class EscalonCompra:
    precio: float
    gasto: float | None  # None si no dijiste cuánto meter

    @property
    def cantidad(self) -> float | None:
        return None if self.gasto is None else self.gasto / self.precio


@dataclass(frozen=True)
class EscaleraCompra:
    coin_id: str
    escalones: list[EscalonCompra]  # de arriba abajo, en el orden en que saltan
    gasto: float | None
    antes: Posicion | None
    ahora: float

    @property
    def comprado(self) -> float | None:
        if self.gasto is None:
            return None
        return sum(e.cantidad for e in self.escalones)

    @property
    def media(self) -> float | None:
        """A cuánto te sale cada una si se compran todos los escalones."""
        if self.comprado is None:
            return None
        return self.gasto / self.comprado

    @property
    def media_antes(self) -> float | None:
        a = self.antes
        if a is None or a.invertido is None or a.cantidad <= 0:
            return None
        return a.invertido / a.cantidad

    @property
    def media_despues(self) -> float | None:
        """Tu precio medio con lo de antes más todo lo de la escalera."""
        if self.comprado is None:
            return None
        if self.antes is None:
            return self.media
        if self.media_antes is None:
            return None
        return (self.antes.invertido + self.gasto) / (
            self.antes.cantidad + self.comprado
        )


def interpretar_compra(argumento: str) -> tuple[str, list[float], float | None]:
    """'compra btc 60k 50k con 900' -> ('bitcoin', [60000, 50000], 900.0)."""
    partes = argumento.split()[1:]
    gasto = None
    if "con" in partes:
        i = partes.index("con")
        if i != len(partes) - 2:
            raise EscaleraError(
                f"Lo que metes va al final, con 'con' delante: {EJEMPLO_COMPRA}"
            )
        gasto = numero(partes[-1])
        if gasto is None or gasto <= 0:
            raise EscaleraError(
                f"'{partes[-1]}' no es una cantidad de dinero. Ej: {EJEMPLO_COMPRA}"
            )
        partes = partes[:i]

    if len(partes) < 1 + MINIMO:
        raise EscaleraError(f"Pon la cripto y al menos dos precios: {EJEMPLO_COMPRA}")
    # Al bajar salta antes el más alto, así que van de arriba abajo.
    precios = _precios(partes[1:], EJEMPLO_COMPRA)[::-1]
    return a_id(partes[0]), precios, gasto


def calcular_compra(
    coin_id: str,
    precios: list[float],
    gasto: float | None,
    ahora: float,
    antes: Posicion | None,
) -> EscaleraCompra:
    if precios[0] >= ahora:
        raise EscaleraError(
            "El primer escalón tiene que estar por debajo del precio de ahora. "
            "Si ya está ahí, eso es comprar, no una escalera."
        )
    parte = None if gasto is None else gasto / len(precios)
    escalones = [EscalonCompra(p, parte) for p in precios]
    return EscaleraCompra(coin_id, escalones, gasto, antes, ahora)


def nota_compra(numero: int, de: int, gasto: str | None) -> str:
    if gasto is None:
        return f"Escalera de compra {numero}/{de}"
    return f"Escalera de compra {numero}/{de}: mete {gasto}"
