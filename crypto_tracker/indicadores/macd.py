"""/macd: si una cripto coge o pierde empuje, con las medias de 12 y 26 días."""

from dataclasses import dataclass
from datetime import date

# Los de siempre, los que salen en cualquier web de gráficas.
RAPIDA = 12
LENTA = 26
SEÑAL = 9

# La primera señal sale el día 34; con 90 las medias ya se han asentado.
HORAS = 90 * 24
MINIMO = LENTA + SEÑAL - 1


@dataclass(frozen=True)
class Macd:
    macd: float  # media de 12 menos media de 26, en dinero
    señal: float
    ahora: float
    hist_ayer: float
    cruce_hace: int | None  # días desde que cruzó su señal; None si no se ve
    dias: int

    @property
    def histograma(self) -> float:
        return self.macd - self.señal

    @property
    def arriba(self) -> bool:
        return self.histograma > 0

    @property
    def cogiendo_fuerza(self) -> bool:
        return abs(self.histograma) > abs(self.hist_ayer)


def calcular(dias: list[tuple[date, float]]) -> Macd | None:
    """None si no hay MINIMO días seguidos con precio. dias sale de por_dias."""
    # Solo el último tramo sin huecos, como en /rsi.
    inicio = len(dias) - 1
    while inicio > 0 and (dias[inicio][0] - dias[inicio - 1][0]).days == 1:
        inicio -= 1
    precios = [p for _, p in dias[inicio:]]
    if len(precios) < MINIMO + 1:
        return None

    rapida = _media(precios, RAPIDA)
    lenta = _media(precios, LENTA)
    # Las dos empiezan a la vez el día 26: antes la lenta no existe.
    lineas = [r - le for r, le in zip(rapida[LENTA - RAPIDA :], lenta, strict=True)]
    señal = _media(lineas, SEÑAL)
    hist = [m - s for m, s in zip(lineas[SEÑAL - 1 :], señal, strict=True)]

    cruce = next(
        (
            len(hist) - 1 - i
            for i in range(len(hist) - 1, 0, -1)
            if (hist[i] > 0) != (hist[i - 1] > 0)
        ),
        None,
    )
    return Macd(lineas[-1], señal[-1], precios[-1], hist[-2], cruce, len(precios))


def _media(valores: list[float], n: int) -> list[float]:
    """Media exponencial, empezando por la normal de los n primeros. Sale una
    por cada valor a partir del n-ésimo."""
    k = 2 / (n + 1)
    medias = [sum(valores[:n]) / n]
    for v in valores[n:]:
        medias.append(v * k + medias[-1] * (1 - k))
    return medias
