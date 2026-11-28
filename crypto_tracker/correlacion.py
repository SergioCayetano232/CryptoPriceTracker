"""/correlacion: si dos criptos suben y bajan a la vez, o todas contra todas."""

import math
from dataclasses import dataclass
from datetime import date, timedelta

from .nucleo.periodo import PeriodoError, es_tramo, leer
from .nucleo.simbolos import a_id

POR_DEFECTO = 30 * 24

EJEMPLO = "/correlacion btc eth 30d"

# Con menos cambios de día, una casualidad ya da una correlación muy alta.
MINIMO = 7

TODAS = "todas"
# Con más, las casillas no caben en el móvil ni con dos decimales.
MAX_TODAS = 8


@dataclass(frozen=True)
class Correlacion:
    valor: float  # de -1 (al revés) a 1 (iguales)
    dias: int  # cuántos cambios de día se han comparado


def interpretar(argumento: str) -> tuple[list[str], float]:
    """'btc eth 7d' -> (['bitcoin', 'ethereum'], 168). Sin criptos, [].
    'todas 90d' -> (['todas'], 2160): las que vigilo y las de tu cartera."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if [p.lower() for p in partes] == [TODAS]:
        return [TODAS], horas
    if len(partes) not in (0, 2):
        raise PeriodoError(f"De dos en dos. Escríbelo así: {EJEMPLO}")
    ids = [a_id(p) for p in partes]
    if ids and ids[0] == ids[1]:
        raise PeriodoError("Son la misma cripto: claro que van juntas")
    return ids, horas


def _cambios(dias: list[tuple[date, float]]) -> dict[date, float]:
    """El % de cada día respecto al anterior, solo si hay precio de los dos."""
    precios = dict(dias)
    return {
        d: precios[d] / precios[d - timedelta(days=1)] - 1
        for d in precios
        if d - timedelta(days=1) in precios
    }


def calcular(
    una: list[tuple[date, float]], otra: list[tuple[date, float]]
) -> Correlacion | None:
    """None si no hay MINIMO días en común, o si una no se ha movido nada."""
    a, b = _cambios(una), _cambios(otra)
    comunes = sorted(a.keys() & b.keys())
    if len(comunes) < MINIMO:
        return None

    xs = [a[d] for d in comunes]
    ys = [b[d] for d in comunes]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if not vx or not vy:
        return None
    return Correlacion(cov / math.sqrt(vx * vy), len(comunes))


@dataclass(frozen=True)
class Matriz:
    ids: list[str]
    # Cada pareja una vez, en el orden de ids. None si no hay días en común.
    parejas: dict[tuple[str, str], Correlacion | None]

    def de(self, una: str, otra: str) -> float | None:
        if una == otra:
            return 1.0
        c = self.parejas.get((una, otra)) or self.parejas.get((otra, una))
        return None if c is None else c.valor

    @property
    def con_valor(self) -> list[tuple[str, str, float]]:
        """Las parejas que se han podido medir, de más juntas a menos."""
        lista = [(a, b, c.valor) for (a, b), c in self.parejas.items() if c]
        return sorted(lista, key=lambda x: x[2], reverse=True)

    @property
    def media(self) -> float | None:
        valores = [v for _, _, v in self.con_valor]
        return sum(valores) / len(valores) if valores else None


def juntar(*listas: list[str]) -> list[str]:
    """Las de varias listas sin repetir, en orden y hasta MAX_TODAS."""
    return list(dict.fromkeys(c for lista in listas for c in lista))[:MAX_TODAS]


def matriz(series: dict[str, list[tuple[date, float]]]) -> Matriz:
    ids = list(series)
    parejas = {
        (a, b): calcular(series[a], series[b])
        for i, a in enumerate(ids)
        for b in ids[i + 1 :]
    }
    return Matriz(ids, parejas)
