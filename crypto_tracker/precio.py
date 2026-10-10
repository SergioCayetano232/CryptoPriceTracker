"""/precio: lo que vale una cripto y como va en 24 h y en una semana."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Precio:
    coin_id: str
    precio: float
    en_24h: float | None  # en %
    en_7d: float | None


def leer(datos) -> dict[str, Precio]:
    """Saca lo de /coins/markets con price_change_percentage=24h,7d."""
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
        )
    return precios


def _numero(valor) -> float | None:
    if isinstance(valor, (int, float)) and math.isfinite(valor):
        return float(valor)
    return None
