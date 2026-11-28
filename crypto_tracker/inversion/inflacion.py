"""/inflacion: si tu cartera le gana a la subida de precios en España."""

from dataclasses import dataclass
from datetime import date, datetime

import requests

from .movimientos import Movimiento
from .rentabilidad import calcular as rentabilidad
from .rentabilidad import contables

# El IPCA de España. Eurostat pasó a este conjunto en 2026; el de antes,
# prc_hicp_midx, se quedó en diciembre de 2025. Lo mismo el IPC del INE.
URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_minr"
)
PARAMS = {"geo": "ES", "coicop18": "TOTAL", "unit": "I15"}
TIMEOUT = 20


class InflacionError(Exception):
    """No se pudo leer el IPC."""


@dataclass(frozen=True)
class Inflacion:
    vale: float  # lo que te queda, a precio de hoy
    puesto: float  # lo metido menos lo sacado, tal cual
    necesario: float  # eso mismo, con la subida de precios de cada fecha
    subida: float  # cuánto han subido los precios desde la primera compra, en %
    desde: datetime
    hasta: date  # el último mes con IPC publicado
    fuera: int

    @property
    def diferencia(self) -> float:
        return self.vale - self.necesario

    @property
    def de_verdad(self) -> float | None:
        """Lo que gana en poder de compra, en %."""
        if self.necesario <= 0:
            return None
        return (self.vale / self.necesario - 1) * 100


def pedir() -> dict[date, float]:
    try:
        respuesta = requests.get(URL, params=PARAMS, timeout=TIMEOUT)
        respuesta.raise_for_status()
        datos = respuesta.json()
    except requests.RequestException as e:
        raise InflacionError(f"Eurostat no contesta: {e}") from e
    except ValueError as e:
        raise InflacionError("Eurostat devolvió algo que no es JSON") from e
    ipc = leer(datos)
    if not ipc:
        raise InflacionError("Eurostat no ha dado el IPC")
    return ipc


def leer(datos) -> dict[date, float]:
    """{primer día del mes: índice}. Viene en JSON-stat: los valores van por
    posición y la posición de cada mes está en otra parte."""
    try:
        meses = datos["dimension"]["time"]["category"]["index"]
        valores = datos["value"]
    except (KeyError, TypeError):
        return {}
    if not isinstance(meses, dict) or not isinstance(valores, dict):
        return {}

    ipc = {}
    for mes, posicion in meses.items():
        valor = valores.get(str(posicion))
        try:
            año, numero = (int(x) for x in str(mes).split("-"))
            dia = date(año, numero, 1)
        except ValueError:
            continue
        if isinstance(valor, int | float) and not isinstance(valor, bool) and valor > 0:
            ipc[dia] = float(valor)
    return dict(sorted(ipc.items()))


def indice(ipc: dict[date, float], cuando: date) -> float:
    """El de ese mes o, si falta, el último anterior. Antes del primero, el primero."""
    mes = date(cuando.year, cuando.month, 1)
    anteriores = [v for d, v in ipc.items() if d <= mes]
    return anteriores[-1] if anteriores else next(iter(ipc.values()))


def calcular(
    lista: list[Movimiento],
    precios: dict[str, float],
    ahora: datetime,
    ipc: dict[date, float],
) -> Inflacion | None:
    """None si no hay compras con precio, falta el de hoy de alguna o no hay IPC."""
    r = rentabilidad(lista, precios, ahora)
    if r is None or not ipc:
        return None

    # Los meses que aún no han salido cuentan como el último publicado.
    hoy = indice(ipc, ahora.date())
    dentro, _ = contables(lista)
    puesto = necesario = 0.0
    for m in dentro:
        signo = 1 if m.tipo == "compra" else -1
        puesto += signo * m.coste
        necesario += signo * m.coste * hoy / indice(ipc, m.cuando.date())

    desde = min(m.cuando for m in dentro if m.tipo == "compra")
    return Inflacion(
        vale=r.vale,
        puesto=max(puesto, 0.0),
        # Si sacaste más de lo que metiste, no hay nada que proteger.
        necesario=max(necesario, 0.0),
        subida=(hoy / indice(ipc, desde.date()) - 1) * 100,
        desde=desde,
        hasta=list(ipc)[-1],
        fuera=r.fuera,
    )
