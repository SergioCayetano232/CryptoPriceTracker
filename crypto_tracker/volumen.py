"""Aviso de cuando una que vigilas mueve mucho más volumen de lo normal."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

# El triple ya no es un día movido: suele haber noticia detrás.
VECES = 3.0
# Para volver a avisar tiene que calmarse antes, o rondando el triple avisaría a ratos.
VUELTA = 2.0

DIAS = 30
# Con menos, lo "normal" sería el último susto.
MIN_DIAS = 7
HORAS = (DIAS + 1) * 24


@dataclass(frozen=True)
class Volumen:
    coin_id: str
    actual: float  # lo negociado en las últimas 24 h
    normal: float
    precio: float
    cambio: float | None  # el precio en 24 h, en %

    @property
    def veces(self) -> float:
        return self.actual / self.normal


def normal(serie: list[tuple[datetime, float]], ahora: datetime) -> float | None:
    """La mediana de lo guardado. None si no hay MIN_DIAS de historia."""
    if not serie or ahora - serie[0][0] < timedelta(days=MIN_DIAS):
        return None
    # Cada dato es de las 24 h de antes: lo de ayer ya lleva dentro el susto de hoy.
    corte = ahora - timedelta(hours=24)
    viejos = [v for cuando, v in serie if cuando <= corte and v > 0]
    return median(viejos) if viejos else None


def toca(v: Volumen, avisado: bool) -> bool:
    return not avisado and v.veces >= VECES


def sigue(v: Volumen, avisado: bool) -> bool:
    """Si se queda apuntado como avisado, para no repetir."""
    if toca(v, avisado):
        return True
    return avisado and v.veces >= VUELTA
