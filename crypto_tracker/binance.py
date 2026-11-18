"""Precios de Binance para cuando CoinGecko no contesta."""

import logging
import math

import requests

from . import estables, simbolos

logger = logging.getLogger(__name__)

# Sin símbolo devuelve todos los pares de golpe. Si pidiera solo los míos, un
# par que Binance no tenga tumbaría la petición entera con un 400.
URL = "https://api.binance.com/api/v3/ticker/price"
TIMEOUT = 15

# Cuántos dólares vale un euro. USDT lo doy por dólar: para un aviso de
# respaldo esa diferencia de céntimos no cambia nada.
EURO = "EURUSDT"
MONEDAS = {"usd", "eur"}

FUENTE = "<i>Precios de Binance: CoinGecko no contestaba</i>"


class BinanceError(Exception):
    """Binance tampoco ha dado los precios."""


def pares(coin_ids: list[str]) -> dict[str, str]:
    """{id: par en USDT} de las que sé cómo se llaman en Binance."""
    out = {}
    for coin_id in coin_ids:
        # Una estable contra USDT no dice nada de si se ha salido de su dólar.
        if coin_id in estables.ESTABLES:
            continue
        simbolo = simbolos.de_id(coin_id)
        if simbolo:
            out[coin_id] = f"{simbolo}USDT"
    return out


def leer(datos, coin_ids: list[str], vs_currency: str) -> dict[str, float]:
    """Saca de la lista de Binance el precio de cada una, ya en su moneda."""
    if vs_currency not in MONEDAS or not isinstance(datos, list):
        return {}
    todos = {}
    for d in datos:
        if not isinstance(d, dict):
            continue
        try:
            valor = float(d.get("price"))
        except (TypeError, ValueError):
            continue
        if math.isfinite(valor) and valor > 0:
            todos[d.get("symbol")] = valor

    cambio = 1.0
    if vs_currency == "eur":
        if EURO not in todos:
            return {}
        cambio = todos[EURO]

    return {
        coin_id: todos[par] / cambio
        for coin_id, par in pares(coin_ids).items()
        if par in todos
    }


def precios(coin_ids: list[str], vs_currency: str = "eur") -> dict[str, float]:
    """Los precios que tenga Binance de estas. {} si no hay nada que pedirle."""
    if vs_currency not in MONEDAS or not pares(coin_ids):
        return {}
    try:
        respuesta = requests.get(URL, timeout=TIMEOUT)
        respuesta.raise_for_status()
        datos = respuesta.json()
    except requests.RequestException as e:
        raise BinanceError(f"Binance tampoco contesta: {e}") from e
    except ValueError as e:
        raise BinanceError("Binance devolvió algo que no es JSON") from e
    return leer(datos, coin_ids, vs_currency)
