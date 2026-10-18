"""/precio: lo que vale una cripto y como va en 1 h, en 24 h y en una semana."""

import math
from dataclasses import dataclass

from . import maximo as maximos


@dataclass(frozen=True)
class Precio:
    coin_id: str
    precio: float
    en_24h: float | None  # en %
    en_7d: float | None
    en_1h: float | None = None
    volumen: float | None = None  # lo negociado en 24 h, en la misma moneda
    puesto: int | None = None  # en capitalizacion; las muy nuevas no tienen
    minimo_24h: float | None = None
    maximo_24h: float | None = None
    emitido: float | None = None  # en % de las que habra como mucho
    tope: float | None = None  # las que habra como mucho; muchas no tienen
    maximo: maximos.Maximo | None = None  # el historico
    en_30d: float | None = None


def leer(datos) -> dict[str, Precio]:
    """Saca lo de /coins/markets con price_change_percentage=1h,24h,7d,30d."""
    precios = {}
    historicos = maximos.leer(datos)
    for d in datos if isinstance(datos, list) else []:
        if not isinstance(d, dict) or not d.get("id"):
            continue
        precio = _numero(d.get("current_price"))
        # Recien salida a veces llega a 0; eso no es un precio.
        if not precio:
            continue
        precios[d["id"]] = Precio(
            d["id"],
            precio,
            _numero(d.get("price_change_percentage_24h_in_currency")),
            _numero(d.get("price_change_percentage_7d_in_currency")),
            _numero(d.get("price_change_percentage_1h_in_currency")),
            _numero(d.get("total_volume")) or None,
            _entero(d.get("market_cap_rank")),
            *_rango_24h(d.get("low_24h"), d.get("high_24h"), precio),
            *_emitido(d.get("circulating_supply"), d.get("max_supply")),
            historicos.get(d["id"]),
            _numero(d.get("price_change_percentage_30d_in_currency")),
        )
    return precios


def en_sats(coin_id: str, precio: float, bitcoin: float | None) -> float | None:
    """Cuántos satoshis vale una. None para el propio bitcoin o sin su precio."""
    if coin_id == "bitcoin" or not bitcoin:
        return None
    return precio / bitcoin * 100_000_000


def _rango_24h(minimo, maximo, precio: float) -> tuple[float | None, float | None]:
    minimo, maximo = _numero(minimo), _numero(maximo)
    # Con uno solo, o al reves, no es un rango que se pueda enseñar.
    if not minimo or not maximo or minimo > maximo:
        return None, None
    # CoinGecko los pone al dia con retraso y el precio de ahora se sale a veces.
    return min(minimo, precio), max(maximo, precio)


def _emitido(circulante, tope) -> tuple[float | None, float | None]:
    circulante, tope = _numero(circulante), _numero(tope)
    # Mas en circulacion que el tope es un dato mal puesto en CoinGecko.
    if not circulante or not tope or circulante > tope:
        return None, None
    return circulante / tope * 100, tope


def _numero(valor) -> float | None:
    if isinstance(valor, (int, float)) and math.isfinite(valor):
        return float(valor)
    return None


def _entero(valor) -> int | None:
    return valor if isinstance(valor, int) and valor > 0 else None
