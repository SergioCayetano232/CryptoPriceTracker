"""/sharpe: cuánto te paga tu cartera por cada susto que te da."""

import math
import re
from dataclasses import dataclass
from datetime import date
from statistics import mean, stdev

EJEMPLO = "/sharpe 90d"

DIAS = 90
MIN_DIAS = 30
MAX_DIAS = 365
# Con menos, una buena semana te pone un sobresaliente.
MIN_CAMBIOS = 30

# La cripto no cierra los fines de semana: el año tiene 365 días, no 252.
AL_AÑO = 365

# De peor a mejor: (hasta, nota).
NOTAS = [
    (0.0, "pierdes: el riesgo no te está pagando"),
    (0.5, "flojo: mucho meneo para lo que ganas"),
    (1.0, "aceptable"),
    (2.0, "bueno"),
    (math.inf, "muy bueno"),
]


class SharpeError(Exception):
    """Lo que escribiste en /sharpe no se entiende."""


@dataclass(frozen=True)
class Sharpe:
    ratio: float
    gana: float  # lo que ha ganado en esos días, en %
    se_mueve: float  # lo que se mueve al año, en %
    contados: int
    nota: str


def interpretar(argumento: str) -> int:
    """'' -> 90. '180d', '180' o '180 días' -> 180."""
    texto = argumento.strip().lower()
    if not texto:
        return DIAS
    m = re.fullmatch(r"(\d+)\s*(d|días?|dias?)?", texto)
    if not m or not MIN_DIAS <= int(m.group(1)) <= MAX_DIAS:
        raise SharpeError(f"Dime de {MIN_DIAS} a {MAX_DIAS} días, como {EJEMPLO}")
    return int(m.group(1))


def nota(ratio: float) -> str:
    return next(texto for hasta, texto in NOTAS if ratio < hasta)


def calcular(dias: list[tuple[date, float]]) -> Sharpe | None:
    """dias es el valor al final de cada día (sale de por_dias). None si hay
    menos de MIN_CAMBIOS días seguidos o no se ha movido nada."""
    # En logaritmos para que el signo cuadre con lo ganado: con medias normales,
    # un +10% y un -10% salen a cero y en realidad has perdido un 1%.
    cambios = [
        math.log(hoy / ayer)
        for (d1, ayer), (d2, hoy) in zip(dias, dias[1:], strict=False)
        if ayer > 0 and hoy > 0 and (d2 - d1).days == 1
    ]
    if len(cambios) < MIN_CAMBIOS:
        return None
    desviacion = stdev(cambios)
    if desviacion == 0:
        return None

    # Sin restar lo que daría un depósito: así se compara igual con bitcoin.
    ratio = mean(cambios) / desviacion * math.sqrt(AL_AÑO)
    return Sharpe(
        ratio=ratio,
        gana=(math.exp(sum(cambios)) - 1) * 100,
        se_mueve=desviacion * math.sqrt(AL_AÑO) * 100,
        contados=len(cambios),
        nota=nota(ratio),
    )
