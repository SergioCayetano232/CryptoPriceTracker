"""FIFO: lo primero que compraste es lo primero que vendes, como cuenta Hacienda."""

import math
from collections import deque
from dataclasses import dataclass

from .config import Posicion
from .movimientos import RESTO, Movimiento


@dataclass(frozen=True)
class Lote:
    cantidad: float
    coste: float | None  # None si no dice lo que costó


def ventas(movimientos: list[Movimiento]) -> list[tuple[Movimiento, float | None]]:
    """Cada venta con lo que costó lo vendido. None si no se puede saber."""
    return _repasar(movimientos)[0]


def coste_de_vender(
    historia: list[Movimiento], antes: Posicion, vendido: float
) -> float | None:
    """Lo que costaría lo que vendes ahora, con los lotes que te quedan."""
    cola = _repasar(historia)[1].get(antes.coin_id, deque())
    _cuadrar(cola, antes)
    return _sacar(cola, vendido)


def lotes(
    movimientos: list[Movimiento], cartera: tuple[Posicion, ...]
) -> dict[str, list[Lote]]:
    """Los lotes que te quedan de cada cripto, el más viejo primero."""
    colas = _repasar(movimientos)[1]
    resultado = {}
    for posicion in cartera:
        cola = colas.get(posicion.coin_id, deque())
        _cuadrar(cola, posicion)
        resultado[posicion.coin_id] = list(cola)
    return resultado


def _repasar(
    movimientos: list[Movimiento],
) -> tuple[list[tuple[Movimiento, float | None]], dict[str, deque[Lote]]]:
    lotes: dict[str, deque[Lote]] = {}
    vendidas = []
    for m in sorted(movimientos, key=lambda m: m.id):
        cola = lotes.setdefault(m.coin_id, deque())
        _cuadrar(cola, m.antes)
        if m.tipo == "venta":
            vendidas.append((m, _sacar(cola, m.cantidad)))
        else:
            cola.append(Lote(m.cantidad, m.coste))
    return vendidas, lotes


def _cuadrar(cola: deque[Lote], posicion: Posicion | None) -> None:
    # Lo del .env no tiene compras detrás: entra como el lote más viejo, que lo
    # es. Y si lo tocaste a mano a medias, manda lo que había en ese momento.
    tenia = posicion.cantidad if posicion else 0.0
    suma = sum(lote.cantidad for lote in cola)
    if math.isclose(suma, tenia, rel_tol=1e-6, abs_tol=RESTO):
        return
    cola.clear()
    if posicion:
        cola.append(Lote(posicion.cantidad, posicion.invertido))


def _sacar(cola: deque[Lote], cantidad: float) -> float | None:
    coste = 0.0
    sin_saber = False
    queda = cantidad
    while cola and queda > RESTO:
        lote = cola.popleft()
        parte = min(lote.cantidad, queda)
        queda -= parte
        coste_parte = None
        if lote.coste is None:
            sin_saber = True
        else:
            coste_parte = lote.coste * parte / lote.cantidad
            coste += coste_parte
        if lote.cantidad - parte > RESTO:
            resto = None if coste_parte is None else lote.coste - coste_parte
            cola.appendleft(Lote(lote.cantidad - parte, resto))

    # Vender más de lo que había en los lotes no sale de ninguna compra.
    return None if sin_saber or queda > RESTO else coste
