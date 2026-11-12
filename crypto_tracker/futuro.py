"""/futuro: entre qué cifras puede estar tu cartera dentro de unos días."""

import math
import re
from dataclasses import dataclass
from datetime import date
from statistics import stdev

EJEMPLO = "/futuro 30d"

DIAS = 30
MAX_DIAS = 365
# Se mide con lo que se ha movido en estos días.
HORAS = 90 * 24
# Con menos cambios de un día a otro, lo que se mueve es casi azar.
MIN_CAMBIOS = 14

# 1 desviación son 2 de cada 3 veces; 1,645, 9 de cada 10.
PROBABLE = 1.0
CASI_SEGURO = 1.645


class FuturoError(Exception):
    """Lo que escribiste en /futuro no se entiende."""


@dataclass(frozen=True)
class Futuro:
    valor: float
    dias: int
    al_dia: float  # lo que se mueve en un día, en %
    contados: int  # cambios de un día a otro que se han usado
    probable: tuple[float, float]
    casi_seguro: tuple[float, float]


def interpretar(argumento: str) -> int:
    """'' -> 30. '90d', '90' o '90 días' -> 90."""
    texto = argumento.strip().lower()
    if not texto:
        return DIAS
    m = re.fullmatch(r"(\d+)\s*(d|días?|dias?)?", texto)
    if not m or not 1 <= int(m.group(1)) <= MAX_DIAS:
        raise FuturoError(f"Dime de 1 a {MAX_DIAS} días, como {EJEMPLO}")
    return int(m.group(1))


def calcular(
    valor: float, dias: list[tuple[date, float]], cuantos: int
) -> Futuro | None:
    """dias es el valor de la cartera al final de cada día (sale de por_dias).
    None si no hay MIN_CAMBIOS cambios de un día al siguiente."""
    # En logaritmos: un -50% y un +100% son lo mismo de grandes, y así no sale
    # nunca una cartera en negativo.
    cambios = [
        math.log(hoy / ayer)
        for (d1, ayer), (d2, hoy) in zip(dias, dias[1:], strict=False)
        if ayer > 0 and hoy > 0 and (d2 - d1).days == 1
    ]
    if len(cambios) < MIN_CAMBIOS:
        return None

    # Sin tendencia: lo que subió en estos 90 días no dice nada de los siguientes.
    sigma = stdev(cambios) * math.sqrt(cuantos)

    def entre(z: float) -> tuple[float, float]:
        return valor * math.exp(-z * sigma), valor * math.exp(z * sigma)

    return Futuro(
        valor=valor,
        dias=cuantos,
        al_dia=stdev(cambios) * 100,
        contados=len(cambios),
        probable=entre(PROBABLE),
        casi_seguro=entre(CASI_SEGURO),
    )
