"""/rentabilidad: lo que ganas al año, contando cuándo metiste y sacaste cada euro."""

from dataclasses import dataclass
from datetime import datetime

from .movimientos import RESTO, Movimiento

# Con menos, pasarlo a anual da cosas como +1.200% por una buena semana.
MIN_DIAS = 30

# Entre -99,99% y +1.000.000% al año: fuera de ahí no hay nada real que buscar.
SUELO, TECHO = -0.9999, 10_000.0


@dataclass(frozen=True)
class Rentabilidad:
    metido: float
    sacado: float
    vale: float  # lo que te queda, a precio de hoy
    dias: int
    anual: float | None  # en %; None con menos de MIN_DIAS o si no sale
    fuera: int  # sin precio, o ventas de lo que venía del .env

    @property
    def ganancia(self) -> float:
        return self.sacado + self.vale - self.metido

    @property
    def porcentaje(self) -> float:
        return self.ganancia / self.metido * 100


def tir(flujos: list[tuple[datetime, float]]) -> float | None:
    """El interés anual que deja todo a cero. Lo que metes va en -, lo que sacas en +.

    Por bisección: más lento que Newton, pero no se escapa nunca.
    """
    inicio = min(f[0] for f in flujos)
    años = [
        ((cuando - inicio).total_seconds() / 86400 / 365, cf) for cuando, cf in flujos
    ]

    def valor(r: float) -> float:
        return sum(cf / (1 + r) ** t for t, cf in años)

    bajo, alto = SUELO, TECHO
    if valor(bajo) * valor(alto) > 0:
        return None
    for _ in range(200):
        medio = (bajo + alto) / 2
        if valor(bajo) * valor(medio) <= 0:
            alto = medio
        else:
            bajo = medio
    return (bajo + alto) / 2


def contables(lista: list[Movimiento]) -> tuple[list[Movimiento], dict[str, float]]:
    """Los que entran en la cuenta, por orden, y lo que te queda de cada una."""
    tienes: dict[str, float] = {}
    dentro = []
    for m in sorted(lista, key=lambda m: m.id):
        if not m.coste:
            continue
        if m.tipo == "compra":
            tienes[m.coin_id] = tienes.get(m.coin_id, 0.0) + m.cantidad
        else:
            # Vender lo que venía del .env sería dinero que sale sin haber entrado.
            if m.cantidad > tienes.get(m.coin_id, 0.0) + RESTO:
                continue
            tienes[m.coin_id] -= m.cantidad
        dentro.append(m)
    return dentro, {c: q for c, q in tienes.items() if q > RESTO}


def calcular(
    lista: list[Movimiento], precios: dict[str, float], ahora: datetime
) -> Rentabilidad | None:
    """None si no hay ninguna compra con precio o falta el de hoy de alguna."""
    dentro, tienes = contables(lista)
    compras = [m for m in dentro if m.tipo == "compra"]
    if not compras or any(c not in precios for c in tienes):
        return None

    metido = sum(m.coste for m in compras)
    sacado = sum(m.coste for m in dentro if m.tipo == "venta")
    vale = sum(q * precios[c] for c, q in tienes.items())
    dias = (ahora - compras[0].cuando).days

    anual = None
    if dias >= MIN_DIAS:
        flujos = [
            (m.cuando, -m.coste if m.tipo == "compra" else m.coste) for m in dentro
        ]
        r = tir([*flujos, (ahora, vale)])
        anual = None if r is None else r * 100

    return Rentabilidad(metido, sacado, vale, dias, anual, len(lista) - len(dentro))
