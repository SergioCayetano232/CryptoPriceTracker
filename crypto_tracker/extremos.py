"""Avisa cuando una cripto marca su maximo o su minimo de los ultimos dias."""

from datetime import datetime, timedelta

from .alerts import ALTO, BAJO, Alert
from .periodo import falta_principio

# En plena subida cada ciclo es un maximo nuevo. Uno al dia ya dice bastante.
ESPERA = timedelta(hours=24)


def revisar(
    coin_id: str,
    precio: float,
    rango: tuple[datetime, float, float] | None,
    ahora: datetime,
    dias: int,
) -> Alert | None:
    """rango es (primer precio guardado, maximo, minimo) del tramo, sin el de ahora."""
    if rango is None:
        return None

    primero, techo, suelo = rango
    # Con tres dias guardados, llamar a algo "maximo de 30 dias" seria mentir.
    if falta_principio(primero, ahora, dias * 24):
        return None

    if precio > techo:
        return Alert(coin_id, precio, techo, ALTO, extremo_dias=dias)
    if precio < suelo:
        return Alert(coin_id, precio, suelo, BAJO, extremo_dias=dias)
    return None


def toca(ultimo: datetime | None, ahora: datetime) -> bool:
    """Si ha pasado bastante desde el ultimo aviso de este tipo."""
    return ultimo is None or ahora - ultimo >= ESPERA
