"""/limite: lo que te permites meter al mes en compras, y el aviso al pasarte."""

from dataclasses import dataclass
from datetime import date

from .movimientos import Movimiento
from .puntuales import numero

EJEMPLO = "/limite 300"

# A partir de aquí la compra ya avisa de lo que queda, antes de pasarse.
CERCA = 80

VER = "ver"
QUITAR = "quitar"
PONER = "poner"


class LimiteError(Exception):
    """Lo que escribiste en /limite no se entiende."""


@dataclass(frozen=True)
class Limite:
    limite: float
    gastado: float  # lo comprado este mes

    @property
    def falta(self) -> float:
        """Lo que queda hasta el límite. Negativo si te has pasado."""
        return self.limite - self.gastado

    @property
    def hecho(self) -> float:
        return self.gastado / self.limite * 100

    @property
    def pasado(self) -> bool:
        return self.gastado > self.limite

    @property
    def cerca(self) -> bool:
        return not self.pasado and self.hecho >= CERCA


def interpretar(argumento: str) -> tuple[str, float | None]:
    """'' -> ver, 'no' -> quitar, '300' -> poner 300."""
    partes = [p for p in argumento.lower().split() if p not in {"€", "$", "£"}]
    if not partes:
        return VER, None
    if partes in (["no"], ["quitar"], ["off"]):
        return QUITAR, None
    cifra = numero(partes[0]) if len(partes) == 1 else None
    if cifra is None or cifra <= 0:
        raise LimiteError(
            f"Escríbelo así: {EJEMPLO} (lo que te permites comprar al mes). "
            "/limite no lo quita"
        )
    return PONER, cifra


def gastado(movimientos: list[Movimiento], hoy: date) -> float:
    """Lo que has metido en compras este mes, en la hora de aquí."""
    # Las recompensas no cuentan: no sale dinero de tu bolsillo.
    return sum(
        m.coste
        for m in movimientos
        if m.tipo == "compra"
        and m.coste
        and (m.cuando.astimezone().year, m.cuando.astimezone().month)
        == (hoy.year, hoy.month)
    )
