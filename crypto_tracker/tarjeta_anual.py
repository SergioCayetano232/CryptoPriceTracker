"""/anual 2025 tarjeta: tu año en una imagen para enseñar, solo con porcentajes."""

from dataclasses import dataclass
from datetime import date

from .anual import Año

PALABRA = "tarjeta"


@dataclass(frozen=True)
class TarjetaAnual:
    año: int
    hasta: date | None  # None si el año ya acabó; si no, hasta cuándo va
    # El primer día con precios, si no es el principio del año. Sin esto un
    # -20% desde octubre parecería del año entero.
    desde: date | None
    total: float | None  # % de la cartera en el año; None sin precios guardados
    meses: dict[int, float]  # mes -> %, solo los que tienen precios
    mejor: tuple[str, float] | None  # la cripto que más subió en el año
    mejor_mes: tuple[int, float] | None
    compras: int
    ventas: int
    mejor_compra: tuple[str, float] | None
    verdes: int  # compras del año que van ganando
    juzgadas: int  # las que tienen con qué compararse


def pedida(argumento: str) -> tuple[bool, str]:
    """'2025 tarjeta' -> (True, '2025'). Da igual el orden."""
    partes = argumento.split()
    quiere = any(p.lower() == PALABRA for p in partes)
    return quiere, " ".join(p for p in partes if p.lower() != PALABRA)


def calcular(a: Año, hoy: date) -> TarjetaAnual | None:
    """None si no hay nada que enseñar: ni precios ni compras de ese año."""
    c = a.cartera
    r = a.mis_compras
    # Un 0% con todo plano no dice nada; mejor que no salga la tarjeta.
    if (c is None or not c.porcentaje) and r is None:
        return None

    mejor = None
    if c is not None and len(c.cambios) > 1:
        mejor = c.cambios[0]
    mejor_compra = None
    if r is not None:
        mejor_compra = (r.mejor.movimiento.coin_id, r.mejor.cambio)
    return TarjetaAnual(
        año=a.año,
        hasta=hoy if a.año == hoy.year else None,
        desde=a.desde if a.desde and a.desde > date(a.año, 1, 2) else None,
        total=c.porcentaje if c is not None and c.porcentaje else None,
        meses=dict(a.meses),
        mejor=mejor,
        mejor_mes=a.mejor_mes,
        compras=a.compras,
        ventas=a.ventas,
        mejor_compra=mejor_compra,
        verdes=r.verdes if r else 0,
        juzgadas=r.total if r else 0,
    )
