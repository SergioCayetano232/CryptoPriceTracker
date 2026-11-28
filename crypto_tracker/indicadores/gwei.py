"""/gwei: lo que cuesta ahora hacer algo en Ethereum."""

import math
from dataclasses import dataclass
from statistics import median

import requests

# Probé varios nodos públicos: Cloudflare no deja pedir más de 10 bloques y
# llamarpc devolvía la página vacía.
URL = "https://ethereum-rpc.publicnode.com"
TIMEOUT = 15
BLOQUES = 20
# Las propinas que se pagaron en esos bloques: las bajas, las de en medio y las altas.
PERCENTILES = [10, 50, 90]
GWEI = 1e9

PRISAS = [
    ("🐢", "Sin prisa"),
    ("🚶", "Normal"),
    ("⚡", "Con prisa"),
]
# Gas que gasta cada cosa. Lo de Uniswap varía con la ruta; esto es lo típico.
OPERACIONES = [
    ("Enviar ETH", 21_000),
    ("Enviar un token (USDT, USDC…)", 65_000),
    ("Un cambio en Uniswap", 150_000),
]


class GweiError(Exception):
    """No se pudo leer del nodo de Ethereum."""


@dataclass(frozen=True)
class Tarifa:
    emoji: str
    nombre: str
    gwei: float  # la base del próximo bloque más la propina

    def eth(self, gas: int) -> float:
        return self.gwei * gas / GWEI


@dataclass(frozen=True)
class Gas:
    base: float  # gwei del próximo bloque, lo que se quema sí o sí
    tarifas: list[Tarifa]  # de la más lenta a la más rápida

    @property
    def normal(self) -> Tarifa:
        return self.tarifas[len(self.tarifas) // 2]


def pedir() -> dict:
    cuerpo = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_feeHistory",
        "params": [BLOQUES, "latest", PERCENTILES],
    }
    try:
        respuesta = requests.post(URL, json=cuerpo, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise GweiError(f"El nodo de Ethereum no contesta: {e}") from e
    try:
        respuesta.raise_for_status()
        datos = respuesta.json()
    except requests.RequestException as e:
        raise GweiError(f"El nodo de Ethereum no contesta: {e}") from e
    except ValueError as e:
        raise GweiError("El nodo de Ethereum devolvió algo que no es JSON") from e
    resultado = datos.get("result") if isinstance(datos, dict) else None
    return resultado if isinstance(resultado, dict) else {}


def _gwei(hexa) -> float | None:
    try:
        valor = int(hexa, 16) / GWEI
    except (TypeError, ValueError):
        return None
    return valor if math.isfinite(valor) and valor >= 0 else None


def leer(datos) -> Gas | None:
    """None si el nodo no trae la base o las propinas."""
    d = datos if isinstance(datos, dict) else {}
    bases = d.get("baseFeePerGas")
    # La última es la del bloque que viene, que es la que vas a pagar.
    base = _gwei(bases[-1]) if isinstance(bases, list) and bases else None
    if base is None:
        return None

    propinas: list[list[float]] = [[] for _ in PERCENTILES]
    for bloque in d.get("reward") or []:
        if not isinstance(bloque, list) or len(bloque) != len(PERCENTILES):
            continue
        valores = [_gwei(x) for x in bloque]
        if None in valores:
            continue
        for lista, valor in zip(propinas, valores, strict=True):
            lista.append(valor)
    if not propinas[0]:
        return None

    # La mediana de los bloques: uno suelto con propinas locas no lo mueve.
    tarifas = [
        Tarifa(emoji, nombre, base + median(lista))
        for (emoji, nombre), lista in zip(PRISAS, propinas, strict=True)
    ]
    return Gas(base, tarifas)
