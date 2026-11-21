"""/comparar: que tal le ha ido a cada cripto en un tramo, de mejor a peor."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .periodo import PeriodoError, es_tramo, falta_principio, leer
from .simbolos import MAX_VARIAS, varias

POR_DEFECTO = 7 * 24

# Mas que esto sin precios nuevos y es que el bot ha estado parado.
VIEJO = timedelta(hours=1)

# Con más líneas la gráfica es un plato de espaguetis y se acaban los colores.
MAX_GRAFICA = 6


@dataclass(frozen=True)
class Resultado:
    coin_id: str
    porcentaje: float
    desde: datetime | None  # solo si no hay precios de todo el tramo
    hasta: datetime | None = None  # solo si el ultimo precio es viejo


def interpretar(argumento: str) -> tuple[list[str], float]:
    """'btc eth 30d' -> (['bitcoin', 'ethereum'], 720). Sin criptos, []."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())

    coin_ids = varias(" ".join(partes))
    if len(coin_ids) > MAX_VARIAS:
        raise PeriodoError(f"Como mucho {MAX_VARIAS} a la vez.")
    return coin_ids, horas


def comparar(
    series: dict[str, list[tuple[datetime, float]]], horas: float, ahora: datetime
) -> tuple[list[Resultado], list[str]]:
    """Las que tienen precios, de la que mas sube a la que mas baja, y las que no."""
    resultados, sin_datos = [], []
    for coin_id, serie in series.items():
        # Con un solo precio no hay nada que comparar.
        if len(serie) < 2 or serie[0][1] <= 0:
            sin_datos.append(coin_id)
            continue
        (primero, antes), (ultimo, despues) = serie[0], serie[-1]
        falta = falta_principio(primero, ahora, horas)
        resultados.append(
            Resultado(
                coin_id,
                (despues / antes - 1) * 100,
                primero if falta else None,
                ultimo if ahora - ultimo > VIEJO else None,
            )
        )

    resultados.sort(key=lambda r: r.porcentaje, reverse=True)
    return resultados, sin_datos


def media(resultados: list[Resultado]) -> float | None:
    """Lo que han hecho todas juntas, a partes iguales. Con una sola, None."""
    if len(resultados) < 2:
        return None
    return sum(r.porcentaje for r in resultados) / len(resultados)


def en_base_100(
    series: dict[str, list[tuple[datetime, float]]], resultados: list[Resultado]
) -> list[tuple[str, list[tuple[datetime, float]]]]:
    """Cada serie empezando en 100, en el orden de resultados, para dibujarlas
    juntas: un BTC de 60.000 y un DOGE de 0,15 no caben en el mismo eje."""
    lineas = []
    for r in resultados:
        serie = series[r.coin_id]
        base = serie[0][1]
        lineas.append((r.coin_id, [(f, p / base * 100) for f, p in serie]))
    return lineas
