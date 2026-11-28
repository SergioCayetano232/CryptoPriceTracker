"""/estocastico: dónde está el precio dentro de lo que se ha movido en 14 días."""

from dataclasses import dataclass
from datetime import date, datetime

# Los de siempre: %K de 14 días y %D, su media de 3.
PERIODO = 14
SUAVIZADO = 3
ALTO = 80
BAJO = 20

HORAS = 60 * 24
MINIMO = PERIODO + SUAVIZADO - 1


@dataclass(frozen=True)
class Vela:
    dia: date
    alto: float
    bajo: float
    cierre: float


@dataclass(frozen=True)
class Estocastico:
    k: float
    d: float
    techo: float  # lo más alto de los últimos PERIODO días
    suelo: float
    ahora: float
    cruce_hace: int | None  # días desde que %K cruzó %D; None si no se ve
    cruce_arriba: bool  # hacia dónde fue ese cruce
    dias: int

    @property
    def zona(self) -> str:
        if self.k >= ALTO:
            return "alto"
        if self.k <= BAJO:
            return "bajo"
        return "medio"


def velas(serie: list[tuple[datetime, float]]) -> list[Vela]:
    """El más alto, el más bajo y el último de cada día, en la hora de aquí."""
    dias: dict[date, list[float]] = {}
    for cuando, precio in serie:
        dias.setdefault(cuando.astimezone().date(), []).append(precio)
    return [Vela(d, max(p), min(p), p[-1]) for d, p in dias.items()]


def calcular(lista: list[Vela]) -> Estocastico | None:
    """None si no hay MINIMO días seguidos con precio."""
    # Solo el último tramo sin huecos, como en /rsi y /macd.
    inicio = len(lista) - 1
    while inicio > 0 and (lista[inicio].dia - lista[inicio - 1].dia).days == 1:
        inicio -= 1
    lista = lista[inicio:]
    if len(lista) < MINIMO + 1:
        return None

    ks = []
    for i in range(PERIODO - 1, len(lista)):
        tramo = lista[i - PERIODO + 1 : i + 1]
        techo = max(v.alto for v in tramo)
        suelo = min(v.bajo for v in tramo)
        # Sin moverse nada en dos semanas, ni arriba ni abajo: en medio.
        if techo == suelo:
            ks.append(50.0)
        else:
            ks.append((lista[i].cierre - suelo) / (techo - suelo) * 100)
    ds = [
        sum(ks[i - SUAVIZADO + 1 : i + 1]) / SUAVIZADO
        for i in range(SUAVIZADO - 1, len(ks))
    ]
    ks = ks[SUAVIZADO - 1 :]

    cruce = next(
        (
            len(ks) - 1 - i
            for i in range(len(ks) - 1, 0, -1)
            if (ks[i] > ds[i]) != (ks[i - 1] > ds[i - 1])
        ),
        None,
    )
    ultimos = lista[-PERIODO:]
    return Estocastico(
        k=ks[-1],
        d=ds[-1],
        techo=max(v.alto for v in ultimos),
        suelo=min(v.bajo for v in ultimos),
        ahora=lista[-1].cierre,
        cruce_hace=cruce,
        cruce_arriba=ks[-1] > ds[-1],
        dias=len(lista),
    )
