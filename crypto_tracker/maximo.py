"""/ath: el maximo historico de una cripto y cuanto le falta para volver."""

import math
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Maximo:
    coin_id: str
    precio: float
    maximo: float
    fecha: datetime

    def falta(self) -> float:
        """Lo que tiene que subir, en %, para volver al maximo. 0 si ya esta."""
        return max(0.0, (self.maximo / self.precio - 1) * 100)


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
            maximos[m.coin_id] = m
    return maximos


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
