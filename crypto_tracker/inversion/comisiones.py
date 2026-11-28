"""/comisiones: lo que llevas pagado en comisiones, por año y por cripto."""

from dataclasses import dataclass

from .movimientos import Movimiento

EJEMPLO = "/comisiones 2026"


class ComisionesError(Exception):
    """Lo que escribiste en /comisiones no se entiende."""


@dataclass(frozen=True)
class Comisiones:
    total: float
    movido: float  # lo que compraste o vendiste en esas operaciones, sin la comisión
    con: int  # operaciones con comisión apuntada
    sin: int  # compras y ventas sin ella
    por_año: dict[int, float]
    por_cripto: dict[str, float]  # de la que más a la que menos

    @property
    def porcentaje(self) -> float | None:
        return self.total / self.movido * 100 if self.movido > 0 else None


def interpretar(argumento: str, este_año: int) -> int | None:
    """'' -> None, todas. '2025' -> solo ese año."""
    texto = argumento.strip()
    if not texto:
        return None
    if not texto.isdigit() or not 2009 <= int(texto) <= este_año:
        raise ComisionesError(f"Dime un año entre 2009 y {este_año}, como {EJEMPLO}")
    return int(texto)


def calcular(lista: list[Movimiento], año: int | None = None) -> Comisiones:
    total = movido = 0.0
    con = sin = 0
    por_año: dict[int, float] = {}
    por_cripto: dict[str, float] = {}
    for m in lista:
        # Las recompensas no pasan por el exchange.
        if m.tipo == "recompensa":
            continue
        cuando = m.cuando.astimezone().year
        if año is not None and cuando != año:
            continue
        if m.comision is None:
            sin += 1
            continue
        con += 1
        total += m.comision
        # En la compra va sumada a lo que te costó y en la venta, restada de lo cobrado.
        if m.coste is not None:
            signo = -1 if m.tipo == "compra" else 1
            movido += m.coste + signo * m.comision
        por_año[cuando] = por_año.get(cuando, 0.0) + m.comision
        por_cripto[m.coin_id] = por_cripto.get(m.coin_id, 0.0) + m.comision

    return Comisiones(
        total=total,
        movido=movido,
        con=con,
        sin=sin,
        por_año=dict(sorted(por_año.items(), reverse=True)),
        por_cripto=dict(sorted(por_cripto.items(), key=lambda c: -c[1])),
    )
