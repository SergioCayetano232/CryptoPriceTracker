"""/rellenar: baja de CoinGecko los precios pasados que el bot no guardó."""

import bisect
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median

from .periodo import PeriodoError, es_tramo
from .periodo import leer as leer_tramo
from .simbolos import varias

EJEMPLO = "/rellenar bitcoin 90d"

# Más de un año no lo da el plan gratis de CoinGecko.
MAXIMO_DIAS = 365
# Con un solo día manda un precio cada 5 minutos, y eso ya lo guarda el bot.
MINIMO_DIAS = 2

Punto = tuple[datetime, float]


class RellenarError(Exception):
    """No se entiende lo que se pide."""


@dataclass(frozen=True)
class Relleno:
    coin_id: str
    nuevos: int
    desde: datetime | None  # el más viejo de los nuevos


def interpretar(argumento: str, history_days: int) -> tuple[list[str], int]:
    """'btc eth 30d' -> (['bitcoin', 'ethereum'], 30). Sin tramo, todo lo que cabe."""
    tope = min(history_days, MAXIMO_DIAS) if history_days > 0 else MAXIMO_DIAS
    partes = argumento.split()
    if not partes or not es_tramo(partes[-1]):
        return varias(" ".join(partes)), tope

    try:
        dias = math.ceil(leer_tramo(partes.pop()) / 24)
    except PeriodoError as e:
        raise RellenarError(str(e)) from None

    if dias < MINIMO_DIAS:
        raise RellenarError(f"Como mínimo {MINIMO_DIAS} días: {EJEMPLO}")
    if dias > MAXIMO_DIAS:
        raise RellenarError(f"Como mucho {MAXIMO_DIAS} días: {EJEMPLO}")
    # Lo de antes de HISTORY_DAYS se borraría en el siguiente ciclo.
    if dias > tope:
        raise RellenarError(
            f"Solo guardo {tope} días, lo demás se borraría. "
            "Si quieres más, sube HISTORY_DAYS en el .env"
        )
    return varias(" ".join(partes)), dias


def leer(data) -> list[Punto]:
    """Saca los precios de la respuesta de market_chart, del más viejo al más nuevo."""
    filas = data.get("prices", []) if isinstance(data, dict) else []
    puntos = []
    for fila in filas:
        if not isinstance(fila, list) or len(fila) != 2:
            continue
        ms, precio = fila
        if not all(isinstance(n, (int, float)) for n in fila):
            continue
        if math.isfinite(precio) and precio > 0:
            cuando = datetime.fromtimestamp(ms / 1000, timezone.utc)
            puntos.append((cuando, float(precio)))
    return sorted(puntos)


def faltan(bajados: list[Punto], guardados: list[datetime]) -> list[Punto]:
    """Los bajados que caen donde no hay nada guardado cerca."""
    if len(bajados) < 2:
        return list(bajados)

    # Algo más de medio hueco: sus horas no caen exactas, y repetir /rellenar
    # no debe duplicar lo que metió la vez anterior.
    pasos = [b[0] - a[0] for a, b in zip(bajados, bajados[1:], strict=False)]
    margen = median(pasos) * 0.6

    fechas = sorted(guardados)
    nuevos = []
    for punto in bajados:
        i = bisect.bisect_left(fechas, punto[0])
        vecinas = fechas[max(i - 1, 0) : i + 1]
        if not any(abs(f - punto[0]) <= margen for f in vecinas):
            nuevos.append(punto)
    return nuevos
