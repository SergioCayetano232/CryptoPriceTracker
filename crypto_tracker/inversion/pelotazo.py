"""/pelotazo: tu mejor compra y la peor, por lo que han subido o bajado."""

from dataclasses import dataclass

from .movimientos import Movimiento


@dataclass(frozen=True)
class Jugada:
    compra: Movimiento
    hoy: float  # lo que vale ahora lo que compraste

    @property
    def cambio(self) -> float:
        return (self.hoy / self.compra.coste - 1) * 100


@dataclass(frozen=True)
class Pelotazo:
    mejor: Jugada
    peor: Jugada | None  # None si solo hay una compra


def calcular(
    movimientos: list[Movimiento], precios: dict[str, float]
) -> Pelotazo | None:
    resultados = [
        Jugada(m, m.cantidad * precios[m.coin_id])
        for m in movimientos
        # Con coste 0 no hay % que sacar; las recompensas ni entran.
        if m.tipo == "compra" and m.coste and m.coin_id in precios
    ]
    if not resultados:
        return None
    resultados.sort(key=lambda r: r.cambio, reverse=True)
    peor = resultados[-1] if len(resultados) > 1 else None
    return Pelotazo(resultados[0], peor)
