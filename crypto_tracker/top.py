"""/top: las que mas suben y las que mas bajan hoy entre las mas grandes."""

import math
from dataclasses import dataclass

# Fuera de las 100 primeras hay mucha moneda pequeña que hace +80% un dia
# cualquiera y se comeria la lista.
ENTRE = 100
CUANTAS = 5


@dataclass(frozen=True)
class Movida:
    coin_id: str
    nombre: str
    simbolo: str
    precio: float
    variacion: float  # en 24 h


def leer(datos) -> list[Movida]:
    """Saca las de /coins/markets que traen precio y variacion."""
    lista = []
    for m in datos if isinstance(datos, list) else []:
        if not isinstance(m, dict) or not m.get("id"):
            continue
        precio = _numero(m.get("current_price"))
        variacion = _numero(m.get("price_change_percentage_24h"))
        if precio is None or variacion is None:
            continue
        lista.append(
            Movida(
                m["id"],
                str(m.get("name") or m["id"]),
                str(m.get("symbol") or "").upper(),
                precio,
                variacion,
            )
        )
    return lista


def separar(lista: list[Movida]) -> tuple[list[Movida], list[Movida]]:
    """(suben, bajan), de la que mas se mueve a la que menos."""
    suben = sorted((m for m in lista if m.variacion > 0), key=lambda m: -m.variacion)
    bajan = sorted((m for m in lista if m.variacion < 0), key=lambda m: m.variacion)
    return suben[:CUANTAS], bajan[:CUANTAS]


def _numero(valor) -> float | None:
    if isinstance(valor, (int, float)) and math.isfinite(valor):
        return float(valor)
    return None
