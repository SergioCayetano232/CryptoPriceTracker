"""/lightning: cuánto bitcoin hay en Lightning y si la red crece o encoge."""

import math
from dataclasses import dataclass

import requests

# mempool.space dejó de actualizar esto en agosto de 2026; 1ml.com sigue al día.
URL = "https://1ml.com/statistics"
TIMEOUT = 15
SATS_POR_BTC = 100_000_000

# Lo que se mueve en un mes cualquiera; de ahí para fuera ya dice algo.
CAMBIO = 5.0

EJEMPLO = "/lightning"


class LightningError(Exception):
    """No se pudo leer de 1ml.com."""


@dataclass(frozen=True)
class Lightning:
    capacidad: float  # en BTC
    dolares: float | None
    nodos: int
    canales: int
    capacidad_mes: float | None  # % en 30 días
    nodos_mes: float | None
    canales_mes: float | None
    nodos_nuevos: int | None  # en 24 h
    canales_nuevos: int | None

    @property
    def por_canal(self) -> float:
        return self.capacidad / self.canales

    @property
    def hacia(self) -> str:
        """'crece', 'encoge' o '' si no hay cambio del mes o es poco."""
        if self.capacidad_mes is None:
            return ""
        if self.capacidad_mes >= CAMBIO:
            return "crece"
        return "encoge" if self.capacidad_mes <= -CAMBIO else ""


def pedir() -> dict:
    try:
        respuesta = requests.get(URL, params={"json": "true"}, timeout=TIMEOUT)
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.RequestException as e:
        raise LightningError(f"1ml.com no contesta: {e}") from e
    except ValueError as e:
        raise LightningError("1ml.com devolvió algo que no es JSON") from e


def _numero(valor) -> float | None:
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        return None
    return float(valor) if math.isfinite(valor) else None


def _entero(valor) -> int | None:
    numero = _numero(valor)
    return int(numero) if numero is not None and numero >= 0 else None


def leer(datos) -> Lightning | None:
    """None si falta la capacidad, los nodos o los canales."""
    d = datos if isinstance(datos, dict) else {}
    sats = _numero(d.get("networkcapacity"))
    nodos = _entero(d.get("numberofnodes"))
    canales = _entero(d.get("numberofchannels"))
    if not sats or sats <= 0 or not nodos or not canales:
        return None
    dolares = _numero(d.get("networkcapacityusd"))
    return Lightning(
        capacidad=sats / SATS_POR_BTC,
        dolares=dolares if dolares and dolares > 0 else None,
        nodos=nodos,
        canales=canales,
        capacidad_mes=_numero(d.get("networkcapacity30dchange")),
        nodos_mes=_numero(d.get("numberofnodes30dchange")),
        canales_mes=_numero(d.get("numberofchannels30dchange")),
        nodos_nuevos=_entero(d.get("newnodes24h")),
        canales_nuevos=_entero(d.get("newchannels24h")),
    )
