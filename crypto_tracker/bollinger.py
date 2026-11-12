"""/bollinger: si el precio se ha salido de su banda normal."""

from dataclasses import dataclass
from datetime import date
from statistics import mean, pstdev

# Los de siempre: media de 20 días y dos desviaciones a cada lado.
PERIODO = 20
DESVIACIONES = 2

HORAS = 90 * 24

# Si la banda es de las más estrechas de lo que hay guardado, está comprimida.
ESTRECHA = 0.10


@dataclass(frozen=True)
class Bandas:
    alta: float
    media: float
    baja: float
    ahora: float
    ancho: float  # de la baja a la alta, en % de la media
    estrecha: bool | None  # None si no hay días para comparar el ancho
    dias: int

    @property
    def posicion(self) -> float:
        """0 en la banda baja y 100 en la alta. Si se sale, menos de 0 o más de 100."""
        return (self.ahora - self.baja) / (self.alta - self.baja) * 100

    @property
    def zona(self) -> str:
        if self.ahora > self.alta:
            return "encima"
        return "debajo" if self.ahora < self.baja else "dentro"


def _bandas(precios: list[float]) -> tuple[float, float, float]:
    media = mean(precios)
    desvio = pstdev(precios) * DESVIACIONES
    return media + desvio, media, media - desvio


def calcular(dias: list[tuple[date, float]]) -> Bandas | None:
    """dias es el último precio de cada día, hoy al final (sale de por_dias).
    None si no hay PERIODO días seguidos o el precio no se ha movido nada."""
    # Solo el último tramo sin huecos, como en /rsi.
    inicio = len(dias) - 1
    while inicio > 0 and (dias[inicio][0] - dias[inicio - 1][0]).days == 1:
        inicio -= 1
    precios = [p for _, p in dias[inicio:]]
    if len(precios) < PERIODO:
        return None

    alta, media, baja = _bandas(precios[-PERIODO:])
    if alta == baja:
        return None

    anchos = []
    for fin in range(PERIODO, len(precios) + 1):
        a, m, b = _bandas(precios[fin - PERIODO : fin])
        anchos.append((a - b) / m)
    ancho = anchos[-1]
    # Con menos de un mes de anchos, "de las más estrechas" no dice nada.
    estrecha = None
    if len(anchos) >= 30:
        estrecha = sum(a < ancho for a in anchos) < len(anchos) * ESTRECHA

    return Bandas(alta, media, baja, precios[-1], ancho * 100, estrecha, len(precios))
