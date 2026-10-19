"""/racha: cuántos días seguidos lleva una cripto subiendo o bajando."""

from dataclasses import dataclass
from datetime import date

# Más atrás no miro. Si la racha llega hasta ahí, sale como "al menos".
HORAS = 90 * 24


@dataclass(frozen=True)
class Racha:
    sube: bool
    dias: int
    desde: date  # el día del que se parte, el último antes de la racha
    antes: float
    ahora: float
    entera: bool  # False si se acaban los datos (o hay un hueco) antes que la racha

    @property
    def cambio(self) -> float:
        return (self.ahora / self.antes - 1) * 100


def calcular(dias: list[tuple[date, float]]) -> Racha | None:
    """Cuenta de hoy hacia atrás. None si no hay dos días seguidos con precio.

    dias es el último precio de cada día, hoy al final (sale de por_dias).
    """
    if len(dias) < 2:
        return None

    sube = None
    cuantos = 0
    i = len(dias) - 1
    entera = False
    while i > 0:
        (ayer, anterior), (dia, precio) = dias[i - 1], dias[i]
        # Con el bot parado no sé qué pasó esos días: la cuento hasta ahí.
        if (dia - ayer).days != 1:
            break
        if precio == anterior:
            entera = True
            break
        if sube is None:
            sube = precio > anterior
        elif (precio > anterior) != sube:
            entera = True
            break
        cuantos += 1
        i -= 1

    if not cuantos:
        return None
    desde, antes = dias[i]
    return Racha(sube, cuantos, desde, antes, dias[-1][1], entera)


def mas_larga(dias: list[tuple[date, float]], sube: bool) -> int:
    """La racha más larga hacia ese lado en todos los días que hay."""
    mejor = actual = 0
    for (ayer, anterior), (dia, precio) in zip(dias, dias[1:], strict=False):
        seguido = (dia - ayer).days == 1 and precio != anterior
        actual = actual + 1 if seguido and (precio > anterior) == sube else 0
        mejor = max(mejor, actual)
    return mejor
