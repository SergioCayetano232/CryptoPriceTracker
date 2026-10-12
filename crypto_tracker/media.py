"""/media: las medias de los últimos días y si el precio está por encima."""

from datetime import date, timedelta

from .periodo import PeriodoError, es_tramo, leer
from .simbolos import a_id

# Las de siempre: la semana, el mes y el trimestre.
VENTANAS = (7, 30, 90)

EJEMPLO = "/media bitcoin 30d"

# Con algún día suelto sin datos la media sigue valiendo; con media ventana vacía, no.
COBERTURA = 0.8


def interpretar(argumento: str) -> tuple[str, tuple[int, ...]]:
    """'bitcoin 30d' -> ('bitcoin', (30,)). Sin tramo, las tres; sin cripto, ''."""
    partes = argumento.split()
    ventanas = VENTANAS
    if partes and es_tramo(partes[-1]):
        dias = leer(partes.pop()) / 24
        if dias < 2 or dias != int(dias):
            raise PeriodoError("Tiene que ser en días, de 2 en adelante: 7d, 30d...")
        ventanas = (int(dias),)
    if len(partes) > 1:
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")
    return (a_id(partes[0]) if partes else ""), ventanas


def calcular(dias: list[tuple[date, float]], ventana: int) -> float | None:
    """La media del último precio de cada día. None si faltan muchos días."""
    if not dias:
        return None
    desde = dias[-1][0] - timedelta(days=ventana - 1)
    dentro = [p for dia, p in dias if dia >= desde]
    if len(dentro) < ventana * COBERTURA:
        return None
    return sum(dentro) / len(dentro)
