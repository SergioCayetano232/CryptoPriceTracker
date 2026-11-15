"""/estacional: qué meses del año suele subir o bajar una cripto."""

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median

import requests

# CoinGecko gratis no pasa de un año atrás; las velas de Binance llegan a 2017.
URL = "https://api.binance.com/api/v3/klines"
TIMEOUT = 15

MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]

# Con menos años, que un mes salga bueno es casi azar.
POCOS_AÑOS = 4


class EstacionalError(Exception):
    """No se pudo leer de Binance."""


@dataclass(frozen=True)
class Mes:
    mes: int  # 1 es enero
    suele: float  # la mediana de lo que hizo ese mes, en %
    subio: int
    veces: int


@dataclass(frozen=True)
class Estacional:
    meses: list[Mes]  # solo los que tienen dato, de enero a diciembre
    desde: int  # el año del primer mes contado
    años: int  # las veces que sale el mes que más sale

    @property
    def mejor(self) -> Mes:
        return max(self.meses, key=lambda m: m.suele)

    @property
    def peor(self) -> Mes:
        return min(self.meses, key=lambda m: m.suele)

    def de(self, mes: int) -> Mes | None:
        return next((m for m in self.meses if m.mes == mes), None)


def pedir(par: str):
    try:
        respuesta = requests.get(
            URL,
            params={"symbol": par, "interval": "1M", "limit": 1000},
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        raise EstacionalError(f"Binance no contesta: {e}") from e
    if respuesta.status_code == 400:
        raise EstacionalError("sin datos")
    if respuesta.status_code == 451:
        raise EstacionalError("Binance no deja mirarlo desde este país")
    try:
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.RequestException as e:
        raise EstacionalError(f"Binance no contesta: {e}") from e
    except ValueError as e:
        raise EstacionalError("Binance devolvió algo que no es JSON") from e


def leer(velas, ahora: datetime) -> list[tuple[datetime, float]]:
    """(primer día del mes, lo que hizo en %) de los meses ya cerrados."""
    filas = [v for v in (velas if isinstance(velas, list) else []) if _vale(v)]
    # El primero casi nunca es entero: empezó a cotizar a mitad de mes.
    filas = filas[1:]
    meses = []
    for v in filas:
        cierre = datetime.fromtimestamp(v[6] / 1000, timezone.utc)
        if cierre > ahora:
            continue
        abre, cierra = float(v[1]), float(v[4])
        inicio = datetime.fromtimestamp(v[0] / 1000, timezone.utc)
        meses.append((inicio, (cierra / abre - 1) * 100))
    return meses


def _vale(v) -> bool:
    try:
        return (
            isinstance(v, list)
            and len(v) > 6
            and float(v[1]) > 0
            and float(v[4]) > 0
            and isinstance(v[0], int)
            and isinstance(v[6], int)
        )
    except (TypeError, ValueError):
        return False


def calcular(meses: list[tuple[datetime, float]]) -> Estacional | None:
    if not meses:
        return None
    por_mes: dict[int, list[float]] = {}
    for inicio, cambio in meses:
        por_mes.setdefault(inicio.month, []).append(cambio)

    # La mediana y no la media: el +50% de diciembre de 2017 se comería al resto.
    lista = [
        Mes(m, median(c), sum(1 for x in c if x > 0), len(c))
        for m, c in sorted(por_mes.items())
    ]
    return Estacional(lista, meses[0][0].year, max(m.veces for m in lista))
