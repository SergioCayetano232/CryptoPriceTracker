"""/premium: lo que se paga de más (o de menos) en Coinbase frente a Binance."""

import math
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

COINBASE_URL = "https://api.exchange.coinbase.com/products/{par}/candles"
BINANCE_URL = "https://api.binance.com/api/v3/klines"
TIMEOUT = 15
# Coinbase da 350 velas de una hora: dos semanas largas.
HORAS = 350

# Lo normal es que baile entre -0,1% y +0,1%; de ahí para fuera ya dice algo.
NOTABLE = 0.1

EJEMPLO = "/premium btc"


class PremiumError(Exception):
    """No se pudo leer de Coinbase o de Binance."""


@dataclass(frozen=True)
class Hora:
    cuando: datetime
    prima: float  # % que vale de más en Coinbase


@dataclass(frozen=True)
class Premium:
    simbolo: str
    coinbase: float  # precio de ahora en Coinbase, en dólares
    binance: float  # el de Binance, pasado de USDT a dólares
    horas: list[Hora]  # de la más vieja a la de ahora

    @property
    def ahora(self) -> float:
        return self.horas[-1].prima

    @property
    def media(self) -> float:
        return sum(h.prima for h in self.horas) / len(self.horas)

    @property
    def lado(self) -> str:
        if self.ahora >= NOTABLE:
            return "compran"
        return "venden" if self.ahora <= -NOTABLE else ""


def pedir(simbolo: str) -> tuple[list, list, list]:
    """Las velas de Coinbase en dólares, las del USDT y las de Binance."""
    coinbase = _get(COINBASE_URL.format(par=f"{simbolo}-USD"), {"granularity": 3600})
    usdt = _get(COINBASE_URL.format(par="USDT-USD"), {"granularity": 3600})
    binance = _get(
        BINANCE_URL, {"symbol": f"{simbolo}USDT", "interval": "1h", "limit": HORAS}
    )
    return coinbase, usdt, binance


def _get(url: str, params: dict):
    try:
        respuesta = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise PremiumError(f"{_quien(url)} no contesta: {e}") from e
    # Coinbase da 404 con un par que no tiene; Binance, 400.
    if respuesta.status_code in (400, 404):
        raise PremiumError("sin datos")
    if respuesta.status_code == 451:
        raise PremiumError("Binance no deja mirarlo desde este país")
    try:
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.RequestException as e:
        raise PremiumError(f"{_quien(url)} no contesta: {e}") from e
    except ValueError as e:
        raise PremiumError(f"{_quien(url)} devolvió algo que no es JSON") from e


def _quien(url: str) -> str:
    return "Coinbase" if "coinbase" in url else "Binance"


def _cierres(velas, posicion_hora: int, divisor: int) -> dict[int, float]:
    """{segundo en que empieza la hora: cierre}."""
    cierres = {}
    for v in velas if isinstance(velas, list) else []:
        try:
            hora = int(v[posicion_hora]) // divisor
            cierre = float(v[4])
        except (TypeError, ValueError, IndexError):
            continue
        if cierre > 0 and math.isfinite(cierre):
            cierres[hora] = cierre
    return cierres


def leer(simbolo: str, coinbase, usdt, binance) -> Premium | None:
    """None si no coincide ni una hora entre los tres."""
    # Coinbase: [hora en segundos, mínimo, máximo, apertura, cierre, volumen]
    # Binance: [hora en milisegundos, apertura, máximo, mínimo, cierre, ...]
    en_coinbase = _cierres(coinbase, 0, 1)
    dolar = _cierres(usdt, 0, 1)
    en_binance = _cierres(binance, 0, 1000)

    horas = []
    for hora in sorted(set(en_coinbase) & set(dolar) & set(en_binance)):
        en_dolares = en_binance[hora] * dolar[hora]
        prima = (en_coinbase[hora] / en_dolares - 1) * 100
        horas.append(Hora(datetime.fromtimestamp(hora, timezone.utc), prima))
    if not horas:
        return None

    ultima = max(set(en_coinbase) & set(dolar) & set(en_binance))
    return Premium(
        simbolo,
        en_coinbase[ultima],
        en_binance[ultima] * dolar[ultima],
        horas,
    )
