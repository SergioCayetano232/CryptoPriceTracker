"""/encuesta: cada semana, una encuesta de Telegram con dónde acabará el domingo.

Es /prediccion sin escribir: eliges un tramo, se apunta su centro como tu
predicción y el domingo se mira igual que las demás.
"""

import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from . import prediccion

EJEMPLO = "/encuesta"

# Cada tramo es de este %, hacia arriba y hacia abajo de lo que vale al mandarla.
BANDA = 5
# El centro de cada opción, en % sobre el precio de entonces. Las dos de las
# puntas no tienen fin; les pongo el mismo ancho que a las de dentro.
CENTROS = (-BANDA * 1.5, -BANDA / 2, BANDA / 2, BANDA * 1.5)

# La de cada semana sale de lunes a miércoles, por si el lunes estaba apagado.
DIAS = (0, 1, 2)
HORA = time(9, 0)

_QUITAR = frozenset({"no", "off", "quitar", "quita", "fuera"})


class EncuestaError(Exception):
    """Lo que escribiste en /encuesta no se entiende."""


@dataclass(frozen=True)
class Encuesta:
    """La última que se mandó. Tenerla guardada es tener /encuesta puesto."""

    poll_id: str
    coin_id: str
    entonces: float  # lo que valía al mandarla
    cierre: datetime  # el domingo en que se mira


def interpretar(argumento: str) -> bool:
    """True es ponerla; False, quitarla."""
    palabra = argumento.strip().lower()
    if not palabra:
        return True
    if palabra in _QUITAR:
        return False
    raise EncuestaError("No te entiendo. /encuesta la pone y /encuesta no la quita.")


def limites(entonces: float) -> tuple[float, float]:
    """Los dos precios que separan las opciones de las puntas de las de dentro."""
    return entonces * (1 - BANDA / 100), entonces * (1 + BANDA / 100)


def predicho(entonces: float, opcion: int) -> float | None:
    """El precio que se apunta por esa opción. None si no existe."""
    if not 0 <= opcion < len(CENTROS):
        return None
    return entonces * (1 + CENTROS[opcion] / 100)


def se_cierra(cierre: datetime) -> datetime:
    """Hasta cuándo se puede votar: como /prediccion, un día antes del domingo."""
    return cierre - prediccion.MARGEN


def a_tiempo(e: Encuesta, ahora: datetime) -> bool:
    return ahora < se_cierra(e.cierre)


def toca(ahora: datetime, ultima: Encuesta) -> bool:
    """Si toca mandar la de esta semana."""
    local = ahora.astimezone()
    if local.weekday() not in DIAS or local.time() < HORA:
        return False
    return prediccion.cierre(ahora) != ultima.cierre


def a_texto(e: Encuesta) -> str:
    return json.dumps(
        {
            "poll_id": e.poll_id,
            "coin_id": e.coin_id,
            "entonces": e.entonces,
            "cierre": e.cierre.isoformat(timespec="seconds"),
        }
    )


def de_texto(texto: str | None) -> Encuesta | None:
    """Lo guardado. None si no hay nada o no se entiende."""
    if not texto:
        return None
    try:
        d = json.loads(texto)
        return Encuesta(
            str(d["poll_id"]),
            str(d["coin_id"]),
            float(d["entonces"]),
            datetime.fromisoformat(d["cierre"]),
        )
    except (ValueError, TypeError, KeyError):
        return None


# Lo más lejos que deja Telegram poner el cierre de una encuesta, y lo más cerca.
MAXIMO_TELEGRAM = timedelta(seconds=2_628_000)
MINIMO_TELEGRAM = timedelta(seconds=5)
