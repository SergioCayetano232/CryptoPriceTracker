"""/rsi: si una cripto ha subido o bajado demasiado rápido."""

from dataclasses import dataclass
from datetime import date

# Los 14 días de siempre, los que salen en cualquier web de gráficas.
PERIODO = 14

# Con más días el suavizado se asienta y sale lo mismo que en esas webs.
HORAS = 90 * 24

SOBRECOMPRA = 70
SOBREVENTA = 30


@dataclass(frozen=True)
class Rsi:
    valor: float
    ahora: float
    dias: int  # cuántos días se han usado


def calcular(dias: list[tuple[date, float]]) -> Rsi | None:
    """El RSI de Wilder. None si no hay 15 días seguidos con precio.

    dias es el último precio de cada día, hoy al final (sale de por_dias).
    """
    # Solo el último tramo sin huecos: con el bot parado, el salto de varios
    # días contaría como si fuera de uno.
    inicio = len(dias) - 1
    while inicio > 0 and (dias[inicio][0] - dias[inicio - 1][0]).days == 1:
        inicio -= 1
    precios = [p for _, p in dias[inicio:]]
    if len(precios) < PERIODO + 1:
        return None

    cambios = [b - a for a, b in zip(precios, precios[1:], strict=False)]
    sube = sum(max(c, 0) for c in cambios[:PERIODO]) / PERIODO
    baja = sum(max(-c, 0) for c in cambios[:PERIODO]) / PERIODO
    for c in cambios[PERIODO:]:
        sube = (sube * (PERIODO - 1) + max(c, 0)) / PERIODO
        baja = (baja * (PERIODO - 1) + max(-c, 0)) / PERIODO

    if baja == 0:
        valor = 50.0 if sube == 0 else 100.0
    else:
        valor = 100 - 100 / (1 + sube / baja)
    return Rsi(valor, precios[-1], len(precios))


def hasta_zona(valor: float) -> tuple[float, bool] | None:
    """Puntos para la zona más cerca y si es la de sobrecompra. None si ya está."""
    if valor <= SOBREVENTA or valor >= SOBRECOMPRA:
        return None
    if valor >= 50:
        return SOBRECOMPRA - valor, True
    return valor - SOBREVENTA, False
