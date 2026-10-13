"""/dia: a cuánto estaba una cripto un día concreto."""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .periodo import MAXIMO
from .simbolos import a_id

EJEMPLO = "/dia bitcoin 01/09"

HORAS = MAXIMO

_FECHA = re.compile(r"(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2}|\d{4}))?")

PALABRAS = {"hoy": 0, "ayer": 1, "anteayer": 2}


class DiaError(Exception):
    """Lo que escribiste en /dia no se entiende."""


@dataclass(frozen=True)
class Dia:
    fecha: date
    apertura: float
    cierre: float  # el último del día, o el de ahora si es hoy
    maximo: float
    minimo: float
    ahora: float

    @property
    def en_el_dia(self) -> float:
        return (self.cierre / self.apertura - 1) * 100

    @property
    def desde(self) -> float:
        return (self.ahora / self.cierre - 1) * 100


def leer_fecha(texto: str, hoy: date) -> date | None:
    """'01/09', '1-9-2025', 'ayer'... None si no parece una fecha."""
    texto = texto.lower()
    if texto in PALABRAS:
        return hoy - timedelta(days=PALABRAS[texto])
    encaja = _FECHA.fullmatch(texto)
    if not encaja:
        return None

    dia, mes, año = encaja.groups()
    try:
        if año:
            return date(int(año) + (2000 if len(año) == 2 else 0), int(mes), int(dia))
        fecha = date(hoy.year, int(mes), int(dia))
    except ValueError:
        raise DiaError(f"El {texto} no existe en el calendario") from None
    # Sin año, si aún no ha llegado este año es que hablas del pasado.
    return fecha if fecha <= hoy else fecha.replace(year=hoy.year - 1)


def interpretar(argumento: str, hoy: date) -> tuple[str, date]:
    """'bitcoin 01/09' -> ('bitcoin', date). Sin cripto, ''."""
    partes = argumento.split()
    fecha = leer_fecha(partes.pop(), hoy) if partes else None
    if fecha is None or len(partes) > 1:
        raise DiaError(f"Escríbelo así: {EJEMPLO} (o ayer)")
    if fecha > hoy:
        raise DiaError("Ese día todavía no ha llegado")
    return (a_id(partes[0]) if partes else ""), fecha


def calcular(serie: list[tuple[datetime, float]], fecha: date) -> Dia | None:
    """None si no hay precios de ese día. serie va del más viejo al más nuevo."""
    del_dia = [p for cuando, p in serie if cuando.astimezone().date() == fecha]
    if not del_dia:
        return None
    return Dia(fecha, del_dia[0], del_dia[-1], max(del_dia), min(del_dia), serie[-1][1])


def cercano(serie: list[tuple[datetime, float]], fecha: date) -> date | None:
    """El día con precios más cerca del que pides, para sugerirlo."""
    dias = {cuando.astimezone().date() for cuando, _ in serie}
    # Con empate, el de antes: suele ser lo que se busca.
    return min(dias, key=lambda d: (abs((d - fecha).days), d), default=None)
