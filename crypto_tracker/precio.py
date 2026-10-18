"""/precio: lo que vale una cripto y como va en 1 h, en 24 h y en una semana."""

import math
from dataclasses import dataclass


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


def leer(datos) -> dict[str, Precio]:
    """Saca lo de /coins/markets con price_change_percentage=1h,24h,7d."""
    precios = {}
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
            *_rango_24h(d.get("low_24h"), d.get("high_24h")),
        )
    return precios


def en_sats(coin_id: str, precio: float, bitcoin: float | None) -> float | None:
    """Cuántos satoshis vale una. None para el propio bitcoin o sin su precio."""
    if coin_id == "bitcoin" or not bitcoin:
        return None
    return precio / bitcoin * 100_000_000


def _rango_24h(minimo, maximo) -> tuple[float | None, float | None]:
    minimo, maximo = _numero(minimo), _numero(maximo)
    # Con uno solo, o al reves, no es un rango que se pueda enseñar.
    if not minimo or not maximo or minimo > maximo:
        return None, None
    return minimo, maximo


def _numero(valor) -> float | None:
    if isinstance(valor, (int, float)) and math.isfinite(valor):
        return float(valor)
    return None


def _entero(valor) -> int | None:
    return valor if isinstance(valor, int) and valor > 0 else None
