"""/mvrv: bitcoin frente a lo que pagaron de media los que lo tienen."""

import math
from dataclasses import dataclass
from datetime import date, datetime

import requests

URL = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
TIMEOUT = 30
DESDE = "2011-01-01"
# El primer año la desviación sale de cuatro datos y el Z se dispara a cientos:
# para comparar empiezo después.
CALENTAR = 365

ZONAS = (
    (0, "🧊", "Fondo: vale menos de lo que se pagó de media"),
    (2, "🟢", "Barato para lo que suele"),
    (5, "😐", "En lo normal"),
    (7, "🔥", "Caliente"),
    (float("inf"), "🌋", "Techo: así estaba en 2013 y 2017"),
)


class MvrvError(Exception):
    """No se pudo leer de CoinMetrics."""


@dataclass(frozen=True)
class Dia:
    cuando: date
    precio: float
    mvrv: float
    z: float

    @property
    def realizado(self) -> float:
        """Lo que costó de media cada bitcoin la última vez que se movió."""
        return self.precio / self.mvrv

    @property
    def ganancia(self) -> float:
        """% que ganan de media los que lo tienen."""
        return (self.mvrv - 1) * 100


@dataclass(frozen=True)
class Mvrv:
    dias: list[Dia]  # desde que el Z ya tiene sentido, del más viejo a ayer

    @property
    def hoy(self) -> Dia:
        return self.dias[-1]

    @property
    def por_debajo(self) -> float:
        """% de los días que el Z estuvo más bajo que hoy."""
        return 100 * sum(d.z < self.hoy.z for d in self.dias) / len(self.dias)

    @property
    def maximo(self) -> Dia:
        return max(self.dias, key=lambda d: d.z)

    @property
    def minimo(self) -> Dia:
        return min(self.dias, key=lambda d: d.z)

    @property
    def zona(self) -> tuple[str, str]:
        return next((e, t) for tope, e, t in ZONAS if self.hoy.z < tope)


def pedir() -> list:
    params = {
        "assets": "btc",
        "metrics": "CapMVRVCur,CapMrktCurUSD,PriceUSD",
        "frequency": "1d",
        "start_time": DESDE,
        "page_size": 10_000,
    }
    try:
        respuesta = requests.get(URL, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise MvrvError(f"CoinMetrics no contesta: {e}") from e
    try:
        respuesta.raise_for_status()
        datos = respuesta.json()
    except requests.RequestException as e:
        raise MvrvError(f"CoinMetrics no contesta: {e}") from e
    except ValueError as e:
        raise MvrvError("CoinMetrics devolvió algo que no es JSON") from e
    lista = datos.get("data") if isinstance(datos, dict) else None
    return lista if isinstance(lista, list) else []


def leer(datos) -> Mvrv | None:
    """None si no hay ni un día después del primer año."""
    filas = []
    for d in datos if isinstance(datos, list) else []:
        try:
            cuando = datetime.fromisoformat(d["time"][:10]).date()
            numeros = [float(d[k]) for k in ("CapMrktCurUSD", "CapMVRVCur", "PriceUSD")]
        except (KeyError, TypeError, ValueError):
            continue
        if all(x > 0 and math.isfinite(x) for x in numeros):
            filas.append((cuando, *numeros))
    filas.sort()

    # El Z de cada día con la desviación de la capitalización hasta ese día,
    # como lo calcula todo el mundo: con la de hoy, los techos viejos se aplanan.
    dias = []
    n, media, m2 = 0, 0.0, 0.0
    for i, (cuando, capitalizacion, mvrv, precio) in enumerate(filas):
        n += 1
        delta = capitalizacion - media
        media += delta / n
        m2 += delta * (capitalizacion - media)
        desviacion = math.sqrt(m2 / n)
        if i < CALENTAR or not desviacion:
            continue
        z = (capitalizacion - capitalizacion / mvrv) / desviacion
        dias.append(Dia(cuando, precio, mvrv, z))
    return Mvrv(dias) if dias else None
