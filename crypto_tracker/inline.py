"""Modo inline: escribes @tubot btc en cualquier chat y mandas el precio."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .mensajes.base import SIMBOLOS, _flecha, _nombre, _num
from .simbolos import MAX_VARIAS, varias

# Telegram pregunta con cada letra que escribes. Así se guarda la respuesta
# medio minuto y no vuelve a preguntar si borras y repites.
CACHE = 30

# Con el bot parado el último precio puede ser de hace días. Pasado esto el
# mensaje lo dice, que el que lo recibe no tiene por qué saberlo.
VIEJO = timedelta(hours=1)


@dataclass(frozen=True)
class Tarjeta:
    coin_id: str
    titulo: str
    descripcion: str
    texto: str  # lo que se manda al chat al tocarla, en HTML


def criptos(consulta: str, vigiladas: list[str]) -> list[str]:
    """'btc eth' -> ['bitcoin', 'ethereum']. Vacía, las que vigilas."""
    ids = varias(consulta) if consulta.strip() else vigiladas
    return ids[:MAX_VARIAS]


def hace(guardado: datetime, ahora: datetime) -> str:
    minutos = max(0, int((ahora - guardado).total_seconds() // 60))
    if minutos < 1:
        return "ahora mismo"
    if minutos < 60:
        return f"hace {minutos} min"
    if minutos < 48 * 60:
        return f"hace {minutos // 60} h"
    return f"hace {minutos // (24 * 60)} días"


def tarjeta(
    coin_id: str,
    precio: float,
    variacion: float | None,
    currency: str,
    guardado: datetime | None = None,
    ahora: datetime | None = None,
) -> Tarjeta:
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    # El título va sin HTML, ahí se vería el &amp; tal cual.
    titulo = f"{coin_id.replace('-', ' ').title()}  {simbolo}{_num(precio)}"
    texto = f"💰 <b>{_nombre(coin_id)}</b>  {simbolo}{_num(precio)}"

    if variacion is None:
        descripcion = "Sin datos de las últimas 24 h"
    else:
        descripcion = f"{_flecha(variacion)} {variacion:+.2f}% en 24 h"
        texto += f"\n{descripcion}"

    if guardado is not None and ahora is not None:
        descripcion += f" · {hace(guardado, ahora)}"
        if ahora - guardado > VIEJO:
            texto += f"\n<i>Precio de {hace(guardado, ahora)}</i>"
    return Tarjeta(coin_id, titulo, descripcion, texto)
