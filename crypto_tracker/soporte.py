"""/soporte: los precios donde una cripto ha girado varias veces."""

from dataclasses import dataclass
from datetime import date, datetime

from .periodo import PeriodoError, es_tramo, leer
from .simbolos import a_id

POR_DEFECTO = 90 * 24

EJEMPLO = "/soporte bitcoin 90d"

# Un giro es el máximo o el mínimo de los dos días de antes y los dos de después.
LADO = 2
# Giros a menos de esto entre sí cuentan como el mismo nivel.
TOLERANCIA = 0.02
MIN_TOQUES = 2
MAXIMO = 3  # por cada lado


@dataclass(frozen=True)
class Nivel:
    precio: float
    toques: int
    ultimo: date


@dataclass(frozen=True)
class Soportes:
    precio: float  # el último guardado
    soportes: list[Nivel]  # por debajo, el más cercano primero
    resistencias: list[Nivel]  # por encima, el más cercano primero

    def distancia(self, n: Nivel) -> float:
        return (n.precio / self.precio - 1) * 100


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 30d' -> ('bitcoin', 720). Sin tramo, 90 días; sin cripto, ''."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if len(partes) > 1:
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")
    return (a_id(partes[0]) if partes else ""), horas


def velas(serie: list[tuple[datetime, float]]) -> list[tuple[date, float, float]]:
    """(día, máximo, mínimo) de cada día, en la hora de aquí."""
    dias: dict[date, tuple[float, float]] = {}
    for cuando, precio in serie:
        dia = cuando.astimezone().date()
        alto, bajo = dias.get(dia, (precio, precio))
        dias[dia] = (max(alto, precio), min(bajo, precio))
    return [(d, alto, bajo) for d, (alto, bajo) in dias.items()]


def giros(dias: list[tuple[date, float, float]]) -> list[tuple[date, float]]:
    """Los máximos y mínimos de su entorno. Los de los bordes no: falta un lado."""
    lista = []
    for i in range(LADO, len(dias) - LADO):
        # Estricto: con el precio plano, todos los días serían un giro.
        otros = dias[i - LADO : i] + dias[i + 1 : i + LADO + 1]
        dia, alto, bajo = dias[i]
        if alto > max(a for _, a, _ in otros):
            lista.append((dia, alto))
        if bajo < min(b for _, _, b in otros):
            lista.append((dia, bajo))
    return lista


def agrupar(puntos: list[tuple[date, float]]) -> list[Nivel]:
    """Junta los giros que están cerca. Solo salen los de MIN_TOQUES o más."""
    niveles, grupo = [], []
    for punto in sorted(puntos, key=lambda p: p[1]):
        if grupo and punto[1] > grupo[0][1] * (1 + TOLERANCIA):
            niveles.append(grupo)
            grupo = []
        grupo.append(punto)
    if grupo:
        niveles.append(grupo)
    return [
        Nivel(sum(p for _, p in g) / len(g), len(g), max(d for d, _ in g))
        for g in niveles
        if len(g) >= MIN_TOQUES
    ]


def calcular(serie: list[tuple[datetime, float]]) -> Soportes | None:
    """None si no hay días para un solo giro."""
    dias = velas(serie)
    if len(dias) < 2 * LADO + 1:
        return None
    precio = serie[-1][1]
    # Junto máximos y mínimos: un techo que se rompe suele hacer luego de suelo.
    niveles = agrupar(giros(dias))
    abajo = sorted((n for n in niveles if n.precio < precio), key=lambda n: -n.precio)
    arriba = sorted((n for n in niveles if n.precio >= precio), key=lambda n: n.precio)
    return Soportes(precio, abajo[:MAXIMO], arriba[:MAXIMO])
