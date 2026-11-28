"""/ath: el maximo historico de una cripto, cuanto le falta y su minimo."""

import math
from dataclasses import dataclass, replace
from datetime import datetime


@dataclass(frozen=True)
class Maximo:
    coin_id: str
    precio: float
    maximo: float
    fecha: datetime
    minimo: float | None = None
    fecha_minimo: datetime | None = None

    def falta(self) -> float:
        """Lo que tiene que subir, en %, para volver al maximo. 0 si ya esta."""
        return max(0.0, (self.maximo / self.precio - 1) * 100)

    def desde_minimo(self) -> float | None:
        """Lo que ha subido desde el minimo historico, en %."""
        if self.minimo is None:
            return None
        return max(0.0, (self.precio / self.minimo - 1) * 100)


def falta_a(maximos: dict[str, Maximo], coin_id: str, precio: float) -> float | None:
    """Lo que le falta al maximo desde ese precio, no desde el de la consulta."""
    m = maximos.get(coin_id)
    # El del aviso es el que lees en el mensaje; el de /coins/markets va algo detras.
    return replace(m, precio=precio).falta() if m and precio > 0 else None


def leer(datos) -> dict[str, Maximo]:
    """Saca los maximos de lo que devuelve /coins/markets. Lo que venga raro, fuera."""
    maximos = {}
    for d in datos if isinstance(datos, list) else []:
        try:
            m = Maximo(
                d["id"],
                float(d["current_price"]),
                float(d["ath"]),
                datetime.fromisoformat(d["ath_date"].replace("Z", "+00:00")),
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        # Con una moneda recien salida a veces llegan a 0 o null.
        if m.precio > 0 and m.maximo > 0 and math.isfinite(m.maximo):
            maximos[m.coin_id] = _con_minimo(m, d)
    return maximos


def _con_minimo(m: Maximo, d: dict) -> Maximo:
    # El minimo es un extra: si viene raro, el maximo vale igual.
    try:
        minimo = float(d["atl"])
        fecha = datetime.fromisoformat(d["atl_date"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError, AttributeError):
        return m
    if minimo <= 0 or not math.isfinite(minimo):
        return m
    return replace(m, minimo=minimo, fecha_minimo=fecha)


def hace(fecha: datetime, ahora: datetime) -> str:
    """'hoy', 'hace 12 días', 'hace 7 meses', 'hace 3 años'."""
    dias = (ahora - fecha).days
    if dias < 1:
        return "hoy"
    if dias < 60:
        return "ayer" if dias == 1 else f"hace {dias} días"
    # Un "hace 13 meses" se entiende peor que "hace 1 año".
    if dias < 365:
        return f"hace {dias // 30} meses"
    años = dias // 365
    return "hace 1 año" if años == 1 else f"hace {años} años"
