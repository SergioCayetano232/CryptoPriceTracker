"""/tendencias: las criptos que mas se buscan hoy en CoinGecko."""

import math
from dataclasses import dataclass

# CoinGecko da 15; con mas de 7 la lista y sus botones no caben en el movil.
MAXIMO = 7


@dataclass(frozen=True)
class Tendencia:
    coin_id: str
    nombre: str
    simbolo: str
    puesto: int | None  # en capitalizacion; las muy nuevas no tienen
    variacion: float | None  # en 24 h


def leer(datos, currency: str) -> list[Tendencia]:
    """Saca la lista de lo que devuelve /search/trending, en su orden."""
    monedas = datos.get("coins", []) if isinstance(datos, dict) else []
    tendencias = []
    for m in monedas:
        item = m.get("item") if isinstance(m, dict) else None
        if not isinstance(item, dict) or not item.get("id"):
            continue
        tendencias.append(
            Tendencia(
                item["id"],
                str(item.get("name") or item["id"]),
                str(item.get("symbol") or "").upper(),
                _entero(item.get("market_cap_rank")),
                _variacion(item.get("data"), currency),
            )
        )
    return tendencias[:MAXIMO]


def _entero(valor) -> int | None:
    return valor if isinstance(valor, int) and valor > 0 else None


def _variacion(data, currency: str) -> float | None:
    # El precio solo viene en dolares, pero la variacion si viene en cada moneda.
    data = data if isinstance(data, dict) else {}
    cambios = data.get("price_change_percentage_24h")
    valor = cambios.get(currency.lower()) if isinstance(cambios, dict) else None
    if isinstance(valor, (int, float)) and math.isfinite(valor):
        return float(valor)
    return None
