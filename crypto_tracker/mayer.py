"""/mayer: el precio entre su media de 200 días, para ver si está caro o barato."""

from dataclasses import dataclass
from datetime import datetime, timezone

import requests

URL = "https://api.binance.com/api/v3/klines"
TIMEOUT = 15
DIAS = 200
POR_PEDIDO = 1000
# Bitcoin está en Binance desde 2017: con cuatro de mil llega de sobra.
PEDIDOS = 4

# Los cortes de siempre: por encima de 2,4 Trace Mayer veía burbuja, y por
# debajo de 1 es que está bajo su media del año largo.
ZONAS = (
    (0.8, "🧊", "Muy por debajo de su media de 200 días"),
    (1.0, "🟢", "Por debajo de su media de 200 días"),
    (1.5, "😐", "En lo normal"),
    (2.4, "🔥", "Caliente: bastante por encima de su media"),
    (float("inf"), "🌋", "Recalentado: así estaba en los techos de otros ciclos"),
)
BURBUJA = 2.4

EJEMPLO = "/mayer btc"


class MayerError(Exception):
    """No se pudo leer de Binance."""


@dataclass(frozen=True)
class Dia:
    cuando: datetime
    precio: float
    multiple: float


@dataclass(frozen=True)
class Mayer:
    par: str
    dias: list[Dia]  # los que ya tienen 200 detrás, del más viejo a hoy
    media: float  # la de 200 días de hoy

    @property
    def hoy(self) -> Dia:
        return self.dias[-1]

    @property
    def por_debajo(self) -> float:
        """% de los días que estuvo más bajo que hoy."""
        return (
            100
            * sum(d.multiple < self.hoy.multiple for d in self.dias)
            / len(self.dias)
        )

    @property
    def maximo(self) -> Dia:
        return max(self.dias, key=lambda d: d.multiple)

    @property
    def minimo(self) -> Dia:
        return min(self.dias, key=lambda d: d.multiple)

    @property
    def zona(self) -> tuple[str, str]:
        return next((e, t) for tope, e, t in ZONAS if self.hoy.multiple < tope)


def pedir(par: str) -> list:
    """Las velas diarias desde el principio, pidiendo hacia atrás de mil en mil."""
    velas: list = []
    hasta = None
    for _ in range(PEDIDOS):
        params = {"symbol": par, "interval": "1d", "limit": POR_PEDIDO}
        if hasta is not None:
            params["endTime"] = hasta
        tanda = _get(params)
        if not isinstance(tanda, list) or not tanda:
            break
        velas = tanda + velas
        if len(tanda) < POR_PEDIDO or not _vale(tanda[0]):
            break
        hasta = tanda[0][0] - 1
    return velas


def _get(params: dict):
    try:
        respuesta = requests.get(URL, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise MayerError(f"Binance no contesta: {e}") from e
    if respuesta.status_code == 400:
        raise MayerError("sin datos")
    if respuesta.status_code == 451:
        raise MayerError("Binance no deja mirarlo desde este país")
    try:
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.RequestException as e:
        raise MayerError(f"Binance no contesta: {e}") from e
    except ValueError as e:
        raise MayerError("Binance devolvió algo que no es JSON") from e


def _vale(v) -> bool:
    try:
        return isinstance(v, list) and isinstance(v[0], int) and float(v[4]) > 0
    except (TypeError, ValueError, IndexError):
        return False


def calcular(par: str, velas) -> Mayer | None:
    """None si no lleva 200 días en Binance."""
    cierres = {}
    for v in velas if isinstance(velas, list) else []:
        if _vale(v):
            # Por la fecha: si dos tandas se pisan, no cuenta un día dos veces.
            cierres[v[0]] = float(v[4])
    fechas = sorted(cierres)
    precios = [cierres[f] for f in fechas]
    if len(precios) < DIAS:
        return None

    dias = []
    suma = sum(precios[:DIAS])
    for i in range(DIAS - 1, len(precios)):
        if i >= DIAS:
            suma += precios[i] - precios[i - DIAS]
        cuando = datetime.fromtimestamp(fechas[i] / 1000, timezone.utc)
        dias.append(Dia(cuando, precios[i], precios[i] / (suma / DIAS)))
    return Mayer(par, dias, suma / DIAS)
