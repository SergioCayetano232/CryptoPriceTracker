"""/corregir: cambiar una compra o venta antigua y rehacer las que van detrás."""

import math
from dataclasses import dataclass, replace

from .config import Posicion
from .movimientos import Movimiento, MovimientoError, comprar, vender
from .puntuales import numero

EJEMPLO = "/corregir 12 cantidad 0.02 o /corregir 12 importe 700"

CANTIDAD = "cantidad"
IMPORTE = "importe"
CAMPOS = {"cantidad": CANTIDAD, "importe": IMPORTE, "coste": IMPORTE}


@dataclass(frozen=True)
class Correccion:
    antes: Movimiento  # como estaba
    despues: Movimiento
    campo: str
    historia: list[Movimiento]  # todos los de esa cripto, ya rehechos
    final: Posicion | None
    rehechos: int  # cuántos van detrás del corregido


def interpretar(argumento: str) -> tuple[int, str, str]:
    """'12 importe 700' -> (12, 'importe', '700')."""
    partes = argumento.split()
    if len(partes) != 3 or not partes[0].lstrip("#").isdecimal():
        raise MovimientoError(
            f"Escríbelo así: {EJEMPLO}. El número sale en /movimientos."
        )
    campo = CAMPOS.get(partes[1].lower())
    if campo is None:
        raise MovimientoError(f"Puedo cambiar la cantidad o el importe: {EJEMPLO}")
    return int(partes[0].lstrip("#")), campo, partes[2]


def calcular(
    historia: list[Movimiento],
    numero_mov: int,
    campo: str,
    texto: str,
    actual: Posicion | None,
) -> Correccion:
    """historia son todos los de esa cripto. MovimientoError si no se puede hacer."""
    orden = sorted(historia, key=lambda m: m.id)
    # Sin esto, rehacer pisaría cualquier cosa que no venga de los movimientos.
    if not _cuadra(orden, actual):
        raise MovimientoError(
            "Lo apuntado de esa cripto no cuadra con lo que tienes ahora, así que "
            "prefiero no tocarlo. Mira /movimientos y /cartera"
        )

    original = next(m for m in orden if m.id == numero_mov)
    nuevo = _con_cambio(original, campo, texto)
    if (nuevo.cantidad, nuevo.coste) == (original.cantidad, original.coste):
        raise MovimientoError("Ya está así, no cambio nada.")

    rehecha, final = _rehacer([nuevo if m.id == numero_mov else m for m in orden])
    despues = next(m for m in rehecha if m.id == numero_mov)
    rehechos = sum(m.id > numero_mov for m in orden)
    return Correccion(original, despues, campo, rehecha, final, rehechos)


def _con_cambio(m: Movimiento, campo: str, texto: str) -> Movimiento:
    por_unidad = texto.startswith("@")
    valor = numero(texto.removeprefix("@"))
    if valor is None or (campo == CANTIDAD and por_unidad):
        raise MovimientoError(f"'{texto}' no me vale. Ejemplo: {EJEMPLO}")
    if campo == CANTIDAD:
        if valor <= 0:
            raise MovimientoError("La cantidad tiene que ser mayor que 0.")
        return replace(m, cantidad=valor)
    if valor < 0:
        raise MovimientoError("El importe no puede ser negativo.")
    return replace(m, coste=valor * m.cantidad if por_unidad else valor)


def _aplicar(posicion: Posicion | None, m: Movimiento) -> Posicion | None:
    if m.tipo == "venta":
        try:
            return vender(posicion, m.coin_id, m.cantidad)
        except MovimientoError:
            raise MovimientoError(
                f"Así no cuadra: la venta del {m.cuando.astimezone():%d/%m/%Y} sería "
                "de más de lo que tendrías entonces."
            ) from None
    # Las más viejas pueden no decir lo que costaron.
    if m.coste is None:
        tenias = posicion.cantidad if posicion else 0.0
        return Posicion(m.coin_id, tenias + m.cantidad, None)
    return comprar(posicion, m.coin_id, m.cantidad, m.coste)


def _rehacer(orden: list[Movimiento]) -> tuple[list[Movimiento], Posicion | None]:
    posicion = orden[0].antes
    rehecha = []
    for m in orden:
        rehecha.append(replace(m, antes=posicion))
        posicion = _aplicar(posicion, m)
    return rehecha, posicion


def _cuadra(orden: list[Movimiento], actual: Posicion | None) -> bool:
    try:
        rehecha, final = _rehacer(orden)
    except MovimientoError:
        return False
    return _igual(final, actual) and all(
        _igual(a.antes, b.antes) for a, b in zip(orden, rehecha, strict=True)
    )


def _igual(a: Posicion | None, b: Posicion | None) -> bool:
    if a is None or b is None:
        return a is b
    if (a.invertido is None) != (b.invertido is None):
        return False
    return _cerca(a.cantidad, b.cantidad) and (
        a.invertido is None or _cerca(a.invertido, b.invertido)
    )


def _cerca(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-9)
