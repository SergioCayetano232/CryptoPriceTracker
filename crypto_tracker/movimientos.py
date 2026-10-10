"""Compras y ventas apuntadas por Telegram, encima del PORTFOLIO del .env."""

from dataclasses import dataclass
from datetime import datetime

from .config import Posicion
from .puntuales import numero
from .simbolos import a_id

EJEMPLO_COMPRA = "/compra bitcoin 0.01 600"
EJEMPLO_VENTA = "/venta bitcoin 0.005 o /venta bitcoin todo"

# Lo que queda por debajo de esto son restos de los decimales, no algo que tengas.
RESTO = 1e-9


class MovimientoError(Exception):
    """La compra o la venta no se entiende o no se puede hacer."""


@dataclass(frozen=True)
class Movimiento:
    """Un /compra o un /venta. antes es como estaba la cripto, None si no la tenias."""

    id: int
    coin_id: str
    tipo: str  # "compra" o "venta"
    cantidad: float
    coste: float | None
    antes: Posicion | None
    cuando: datetime


def interpretar_deshacer(argumento: str) -> int | None:
    """'' -> None (la ultima). '12' -> 12, el numero que lleva el boton."""
    if not argumento:
        return None
    if not argumento.isdigit():
        raise MovimientoError(
            "Escribe /deshacer a secas para quitar la última compra o venta."
        )
    return int(argumento)


def interpretar_compra(argumento: str) -> tuple[str, float, float | None]:
    """'bitcoin 0.01 600' -> ('bitcoin', 0.01, 600). Sin coste, None.

    Con @ va el precio de cada una, como sale en el exchange: 'bitcoin 0.01 @60000'.
    """
    partes = argumento.replace("@ ", "@").split()
    if len(partes) not in (2, 3) or partes[-1] == "@":
        raise MovimientoError(
            f"Escríbelo así: {EJEMPLO_COMPRA} (cripto, cantidad y lo que te costó) "
            "o /compra bitcoin 0.01 @60000 (a cuánto te salió cada una). "
            "Sin lo que te costó, la apunto al precio de ahora."
        )

    cantidad = _cantidad(partes[1], EJEMPLO_COMPRA)
    coste = None
    if len(partes) == 3:
        por_unidad = partes[2].startswith("@")
        coste = _numero(partes[2].removeprefix("@"), EJEMPLO_COMPRA)
        if coste < 0:
            raise MovimientoError("Lo que te costó no puede ser negativo.")
        if por_unidad:
            coste *= cantidad
    return a_id(partes[0]), cantidad, coste


def interpretar_venta(argumento: str) -> tuple[str, float | None]:
    """'bitcoin 0.005' -> ('bitcoin', 0.005). 'bitcoin todo' -> ('bitcoin', None)."""
    partes = argumento.split()
    if len(partes) != 2:
        raise MovimientoError(f"Escríbelo así: {EJEMPLO_VENTA}")

    if partes[1].lower() == "todo":
        return a_id(partes[0]), None
    return a_id(partes[0]), _cantidad(partes[1], EJEMPLO_VENTA)


def comprar(
    posicion: Posicion | None, coin_id: str, cantidad: float, coste: float
) -> Posicion:
    if posicion is None:
        return Posicion(coin_id, cantidad, coste)
    # Si no sé lo que costó lo de antes, sumarle esto daría una ganancia falsa.
    invertido = None if posicion.invertido is None else posicion.invertido + coste
    return Posicion(coin_id, posicion.cantidad + cantidad, invertido)


def vender(
    posicion: Posicion | None, coin_id: str, cantidad: float | None
) -> Posicion | None:
    """Lo que te queda. None si lo vendes todo."""
    if posicion is None:
        raise MovimientoError(f"No tienes {coin_id} en la cartera. Mira /cartera")
    if cantidad is None:
        return None
    if cantidad > posicion.cantidad + RESTO:
        raise MovimientoError(
            f"Solo tienes {texto_cantidad(posicion.cantidad)} de {coin_id}."
        )

    queda = posicion.cantidad - cantidad
    if queda <= RESTO:
        return None
    # Lo invertido baja en proporción: lo vendido se lleva su parte de lo que costó.
    invertido = (
        None
        if posicion.invertido is None
        else posicion.invertido * queda / posicion.cantidad
    )
    return Posicion(coin_id, queda, invertido)


def combinar(
    base: tuple[Posicion, ...], cambios: dict[str, Posicion | None]
) -> tuple[Posicion, ...]:
    """Aplica lo de Telegram al .env. None en un cambio es que la vendiste toda."""
    resultado = [cambios.get(p.coin_id, p) for p in base]
    del_env = {p.coin_id for p in base}
    resultado += [p for c, p in cambios.items() if c not in del_env]
    return tuple(p for p in resultado if p is not None)


def buscar(posiciones: tuple[Posicion, ...], coin_id: str) -> Posicion | None:
    return next((p for p in posiciones if p.coin_id == coin_id), None)


def texto_cantidad(valor: float) -> str:
    """0,016 o 1.500: todos los decimales que tenga, hasta 8, como los satoshis."""
    texto = f"{valor:,.8f}".rstrip("0").rstrip(".")
    return texto.replace(",", "@").replace(".", ",").replace("@", ".")


def _cantidad(texto: str, ejemplo: str) -> float:
    valor = _numero(texto, ejemplo)
    if valor <= 0:
        raise MovimientoError("La cantidad tiene que ser mayor que 0.")
    return valor


def _numero(texto: str, ejemplo: str) -> float:
    valor = numero(texto)
    if valor is None:
        raise MovimientoError(f"'{texto}' no es un número. Ejemplo: {ejemplo}")
    return valor
