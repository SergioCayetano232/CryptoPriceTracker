"""Aviso de cuando una sola cripto se come casi toda la cartera."""

from dataclasses import dataclass

from .cartera import Valor
from .riesgo import CAIDA

# Para volver a avisar tiene que bajar esto por debajo del límite. Si no, una
# cripto rondando el 70% daría un aviso cada vez que lo cruza.
MARGEN = 5


@dataclass(frozen=True)
class Concentracion:
    coin_id: str
    peso: float  # el % de la cartera

    @property
    def si_cae(self) -> float:
        """Lo que caería la cartera si esta cae CAIDA."""
        return self.peso * CAIDA / 100


def mayor(valores: list[Valor]) -> Concentracion | None:
    """La que más pesa. None con menos de dos: el 100% de una sola no es noticia."""
    con_valor = [v for v in valores if v.valor > 0]
    if len(con_valor) < 2:
        return None
    total = sum(v.valor for v in con_valor)
    grande = max(con_valor, key=lambda v: v.valor)
    return Concentracion(grande.coin_id, grande.valor / total * 100)


def toca(c: Concentracion | None, limite: float, avisado: str | None) -> bool:
    return c is not None and c.peso >= limite and c.coin_id != avisado


def sigue(c: Concentracion | None, limite: float, avisado: str | None) -> str | None:
    """Si no toca avisar, lo que se queda apuntado: lo de antes o nada."""
    # Si ahora manda otra, o la de antes ya bajó de verdad, se puede volver a avisar.
    if c is None or c.coin_id != avisado or c.peso < limite - MARGEN:
        return None
    return avisado
