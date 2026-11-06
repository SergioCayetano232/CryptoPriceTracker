"""/vsbtc: tu cartera contra haber metido lo mismo en bitcoin, en las mismas fechas."""

from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta

from .movimientos import RESTO, Movimiento

BITCOIN = "bitcoin"

# El bot guarda cada pocos minutos; si lo más cercano está más lejos que esto,
# estaba parado y prefiero no contar esa compra a un precio inventado.
MARGEN = timedelta(hours=12)


@dataclass(frozen=True)
class Contra:
    real: float  # lo que vale hoy lo que compraste y aún tienes
    btc: float  # lo que valdría si todo hubiera ido a bitcoin
    sats: float  # los bitcoin que tendrías
    contados: int
    fuera: int  # los que no he podido contar: sin precio o sin bitcoin de ese día
    desde: datetime

    @property
    def diferencia(self) -> float:
        return self.real - self.btc

    @property
    def ventaja(self) -> float | None:
        if self.btc <= 0:
            return None
        return (self.real / self.btc - 1) * 100


def precio_en(serie: list[tuple[datetime, float]], cuando: datetime) -> float | None:
    """El precio guardado más cercano a cuando, si está a menos de MARGEN."""
    if not serie:
        return None
    i = bisect_left(serie, cuando, key=lambda p: p[0])
    cerca = [serie[j] for j in (i - 1, i) if 0 <= j < len(serie)]
    fecha, precio = min(cerca, key=lambda p: abs(p[0] - cuando))
    return precio if abs(fecha - cuando) <= MARGEN else None


def a_contar(
    lista: list[Movimiento], serie_btc: list[tuple[datetime, float]]
) -> list[tuple[Movimiento, float]]:
    """Los que se pueden comparar, con el bitcoin de ese momento, por orden."""
    contables = []
    for m in sorted(lista, key=lambda m: m.id):
        precio = precio_en(serie_btc, m.cuando)
        if m.coste is not None and precio:
            contables.append((m, precio))
    return contables


def cantidades(contables: list[tuple[Movimiento, float]]) -> dict[str, float]:
    """Lo que te queda de cada una, contando solo esos movimientos."""
    tienes: dict[str, float] = {}
    for m, _ in contables:
        signo = 1 if m.tipo == "compra" else -1
        tienes[m.coin_id] = tienes.get(m.coin_id, 0.0) + signo * m.cantidad
    # Una venta de algo que venía del .env dejaría la cuenta en negativo.
    return {c: q for c, q in tienes.items() if q > RESTO}


def calcular(
    lista: list[Movimiento],
    serie_btc: list[tuple[datetime, float]],
    precios: dict[str, float],
) -> Contra | None:
    """None si no hay nada que comparar o falta el precio de hoy de alguna."""
    contables = a_contar(lista, serie_btc)
    if not contables or BITCOIN not in precios:
        return None

    sats = 0.0
    for m, precio in contables:
        # Al vender sacas el mismo dinero de los dos lados: la comparación es justa.
        signo = 1 if m.tipo == "compra" else -1
        sats += signo * m.coste / precio
    sats = max(sats, 0.0)

    tienes = cantidades(contables)
    if any(c not in precios for c in tienes):
        return None
    real = sum(q * precios[c] for c, q in tienes.items())

    return Contra(
        real=real,
        btc=sats * precios[BITCOIN],
        sats=sats,
        contados=len(contables),
        fuera=len(lista) - len(contables),
        desde=contables[0][0].cuando,
    )
