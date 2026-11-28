"""/binance: lo que tienes de verdad en Binance contra lo que tienes apuntado.

Solo lee. La clave se crea en Binance con permiso de lectura y nada más, y va
en el .env: BINANCE_API_KEY y BINANCE_API_SECRET. Nunca se enseña ni se loguea.
"""

import hashlib
import hmac
import math
import os
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import requests

from .nucleo import simbolos
from .nucleo.config import Posicion

URL = "https://api.binance.com/api/v3/account"
TIMEOUT = 15
# Binance recomienda 5000 como mucho; con algo menos de margen falla si el
# reloj del servidor va un segundo desajustado.
VENTANA_MS = 5000

# Lo que está en Simple Earn flexible sale como LDBTC: es tuyo igual.
PREFIJO_EARN = "LD"
# Dinero, no cripto: no se apunta en la cartera.
DINERO = {"EUR", "USD", "GBP"}

# Por debajo de esto es polvo de comisiones, no algo sin apuntar.
POLVO = 1e-8


class CuentaError(Exception):
    """No hay clave, no vale o Binance no contesta."""


@dataclass(frozen=True)
class Diferencia:
    coin_id: str
    en_binance: float
    apuntado: float

    @property
    def falta(self) -> float:
        """Lo que hay en Binance de más (positivo) o de menos (negativo)."""
        return self.en_binance - self.apuntado

    @property
    def cuadra(self) -> bool:
        return math.isclose(self.en_binance, self.apuntado, rel_tol=1e-6, abs_tol=POLVO)


@dataclass(frozen=True)
class Comparacion:
    diferencias: list[Diferencia]
    desconocidas: list[str]  # lo que hay en Binance y no sé qué es


def claves() -> tuple[str, str] | None:
    clave = os.getenv("BINANCE_API_KEY", "").strip()
    secreto = os.getenv("BINANCE_API_SECRET", "").strip()
    return (clave, secreto) if clave and secreto else None


def firmar(consulta: str, secreto: str) -> str:
    return hmac.new(secreto.encode(), consulta.encode(), hashlib.sha256).hexdigest()


def pedir_saldos(
    clave: str, secreto: str, ahora_ms: int | None = None
) -> dict[str, float]:
    """{activo: cantidad}, con lo bloqueado en órdenes abiertas sumado."""
    ahora_ms = ahora_ms if ahora_ms is not None else int(time.time() * 1000)
    consulta = urlencode(
        {"omitZeroBalances": "true", "recvWindow": VENTANA_MS, "timestamp": ahora_ms}
    )
    url = f"{URL}?{consulta}&signature={firmar(consulta, secreto)}"
    try:
        respuesta = requests.get(url, headers={"X-MBX-APIKEY": clave}, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise CuentaError("Binance no contesta. Prueba en un rato.") from e

    try:
        datos = respuesta.json()
    except ValueError:
        datos = None
    if respuesta.status_code != 200:
        raise CuentaError(_motivo(datos))
    saldos = leer(datos)
    if saldos is None:
        raise CuentaError("Binance ha devuelto algo que no entiendo.")
    return saldos


def _motivo(datos) -> str:
    codigo = datos.get("code") if isinstance(datos, dict) else None
    if codigo == -1021:
        return (
            "Binance dice que la hora de este ordenador va desajustada. "
            "Ponla en hora automática y prueba otra vez."
        )
    if codigo in (-2014, -2015, -1022):
        return (
            "Binance no acepta la clave. Mira que BINANCE_API_KEY y "
            "BINANCE_API_SECRET estén bien copiadas y que tenga permiso de lectura."
        )
    return "Binance no ha querido darme los saldos. Prueba en un rato."


def leer(datos) -> dict[str, float] | None:
    if not isinstance(datos, dict) or not isinstance(datos.get("balances"), list):
        return None
    saldos: dict[str, float] = {}
    for b in datos["balances"]:
        try:
            activo = str(b["asset"]).upper()
            cantidad = float(b["free"]) + float(b["locked"])
        except (KeyError, TypeError, ValueError):
            return None
        if cantidad > POLVO:
            saldos[activo] = saldos.get(activo, 0.0) + cantidad
    return saldos


def comparar(saldos: dict[str, float], cartera: list[Posicion]) -> Comparacion:
    """Cada cripto que está en Binance o apuntada, con las dos cantidades."""
    en_binance: dict[str, float] = {}
    desconocidas = []
    for activo, cantidad in saldos.items():
        if activo in DINERO:
            continue
        coin_id = _coin_id(activo)
        if coin_id is None:
            desconocidas.append(activo)
            continue
        en_binance[coin_id] = en_binance.get(coin_id, 0.0) + cantidad

    apuntado = {p.coin_id: p.cantidad for p in cartera}
    todas = sorted(set(en_binance) | set(apuntado))
    diferencias = [
        Diferencia(c, en_binance.get(c, 0.0), apuntado.get(c, 0.0)) for c in todas
    ]
    return Comparacion(diferencias, sorted(desconocidas))


def _coin_id(activo: str) -> str | None:
    coin_id = simbolos.IDS.get(activo.lower())
    if coin_id is None and activo.startswith(PREFIJO_EARN):
        coin_id = simbolos.IDS.get(activo[len(PREFIJO_EARN) :].lower())
    return coin_id
