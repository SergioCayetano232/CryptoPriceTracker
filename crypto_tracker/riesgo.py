"""/riesgo: cuánto depende tu cartera de una sola cripto y cuánto se mueve."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .cartera import Valor

# Solo el tipo: volatilidad importa alerts, y alerts importa este.
if TYPE_CHECKING:
    from .volatilidad import Volatilidad

HORAS = 30 * 24

# La caída con la que se explica el peso: un 20% en cripto pasa cada dos por tres.
CAIDA = 20

# Lo que se mueve al día de media, en %. En cripto un 2% es un día normal.
TRANQUILA, MOVIDA = 1.5, 3.5

# Si se parecen tanto, decir que una se mueve más es hilar demasiado fino.
PARECIDO = 0.1


@dataclass(frozen=True)
class Riesgo:
    total: float
    mayor: str
    peso: float  # el % que es la mayor
    equivalentes: float  # a cuántas criptos a partes iguales equivale el reparto
    cuantas: int
    movimiento: Volatilidad | None  # el de la cartera; None sin dos días de precios
    btc: float | None  # lo que se mueve bitcoin al día en el mismo tramo

    @property
    def si_cae(self) -> float:
        """Lo que caería la cartera si la mayor cae CAIDA."""
        return self.peso * CAIDA / 100

    @property
    def al_dia(self) -> float | None:
        if self.movimiento is None:
            return None
        return self.total * self.movimiento.media / 100

    @property
    def nivel(self) -> str | None:
        if self.movimiento is None:
            return None
        if self.movimiento.media < TRANQUILA:
            return "bajo"
        return "medio" if self.movimiento.media < MOVIDA else "alto"

    @property
    def contra_btc(self) -> str | None:
        """'más', 'menos' o 'igual' que bitcoin. None si no hay con qué comparar."""
        if self.movimiento is None or not self.btc:
            return None
        # Si solo tienes bitcoin, compararte con bitcoin no dice nada.
        if self.cuantas == 1 and self.mayor == "bitcoin":
            return None
        relacion = self.movimiento.media / self.btc
        if abs(relacion - 1) < PARECIDO:
            return "igual"
        return "más" if relacion > 1 else "menos"


def calcular(
    valores: list[Valor], movimiento: Volatilidad | None, btc: float | None
) -> Riesgo | None:
    """None si la cartera no vale nada."""
    con_valor = [v for v in valores if v.valor > 0]
    total = sum(v.valor for v in con_valor)
    if not total:
        return None

    pesos = [v.valor / total for v in con_valor]
    mayor = max(con_valor, key=lambda v: v.valor)
    # El inverso de la suma de los pesos al cuadrado: con 3 al 33% sale 3; con
    # 80-10-10, 1,5. Dice mejor que "tienes 3" lo repartido que está de verdad.
    equivalentes = 1 / sum(p * p for p in pesos)
    return Riesgo(
        total=total,
        mayor=mayor.coin_id,
        peso=mayor.valor / total * 100,
        equivalentes=equivalentes,
        cuantas=len(con_valor),
        movimiento=movimiento,
        btc=btc,
    )
