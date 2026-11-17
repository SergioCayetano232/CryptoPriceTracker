"""Calma antes de la tormenta: una semana con mucho menos movimiento de lo normal."""

from dataclasses import dataclass
from datetime import date
from statistics import median

VENTANA = 7  # días que mira de una vez
HORAS = 90 * 24
# De las semanas más quietas que hay guardadas: el 10% de abajo.
ESTRECHO = 0.10
# Para volver a avisar tiene que moverse antes, o rondando el corte avisaría a ratos.
VUELTA = 0.30
# Con menos semanas que comparar, "de las más quietas" no significa nada.
MIN_SEMANAS = 30
# Para contar qué pasó después de las otras veces.
DESPUES = 7
MIN_VECES = 2


@dataclass(frozen=True)
class Calma:
    suelo: float
    techo: float
    rango: float  # (techo - suelo) sobre la media de la semana, en %
    normal: float  # el rango de una semana cualquiera, en %
    puesto: float  # de 0 (la semana más quieta guardada) a 1 (la más movida)
    veces: int  # otras semanas así de quietas con otra detrás para mirar
    despues: float | None  # lo que se movió la semana siguiente, de media y sin signo
    dias: int

    @property
    def quieta(self) -> bool:
        return self.puesto < ESTRECHO


def _rango(precios: list[float]) -> float:
    return (max(precios) - min(precios)) / (sum(precios) / len(precios)) * 100


def calcular(dias: list[tuple[date, float]]) -> Calma | None:
    """None si no hay MIN_SEMANAS de historia con la que comparar."""
    cierres = [p for _, p in dias]
    rangos = [
        _rango(cierres[i - VENTANA + 1 : i + 1])
        for i in range(VENTANA - 1, len(cierres))
    ]
    if len(rangos) <= MIN_SEMANAS:
        return None

    actual, antes = rangos[-1], rangos[:-1]
    # Los empates cuentan medio: con todo igual de movido no hay semana "quieta".
    puesto = (
        sum(r < actual for r in antes) + sum(r == actual for r in antes) / 2
    ) / len(antes)
    corte = sorted(antes)[int(len(antes) * ESTRECHO)]

    movimientos = []
    siguiente_libre = 0
    for j, r in enumerate(antes):
        fin = j + VENTANA - 1  # el último día de esa semana
        # Una racha quieta de diez días es una vez, no cuatro que se pisan.
        if j < siguiente_libre or r >= corte or fin + DESPUES >= len(cierres):
            continue
        movimientos.append(abs(cierres[fin + DESPUES] / cierres[fin] - 1) * 100)
        siguiente_libre = j + VENTANA

    semana = cierres[-VENTANA:]
    return Calma(
        min(semana),
        max(semana),
        actual,
        median(antes),
        puesto,
        len(movimientos),
        sum(movimientos) / len(movimientos) if len(movimientos) >= MIN_VECES else None,
        len(cierres),
    )


def toca(c: Calma, avisado: bool) -> bool:
    return not avisado and c.quieta


def sigue(c: Calma, avisado: bool) -> bool:
    """Si se queda apuntado como avisado, para no repetir."""
    if toca(c, avisado):
        return True
    return avisado and c.puesto < VUELTA
