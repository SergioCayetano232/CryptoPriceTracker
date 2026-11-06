"""/calendario: el mes de una cripto, cada día en verde o en rojo."""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

from .mes import MESES
from .simbolos import a_id

EJEMPLO = "/calendario bitcoin octubre"

# Menos que esto sale como 0,0%, y un 0,0% en rojo parece un error.
IGUAL = 0.05


class CalendarioError(Exception):
    """No se entiende qué mes o qué cripto."""


@dataclass(frozen=True)
class Casilla:
    dia: date
    cambio: float | None  # en %; None si ese día o el anterior no tengo precio
    futuro: bool = False


@dataclass(frozen=True)
class Mes:
    año: int
    mes: int
    casillas: list[Casilla]
    # Del cierre del mes anterior al último día; sin él, desde el primero que tenga.
    cambio: float | None

    @property
    def con_dato(self) -> list[Casilla]:
        return [c for c in self.casillas if c.cambio is not None]

    @property
    def verdes(self) -> int:
        return sum(1 for c in self.con_dato if c.cambio > 0)

    @property
    def rojos(self) -> int:
        return sum(1 for c in self.con_dato if c.cambio < 0)

    @property
    def mejor(self) -> Casilla | None:
        return max(self.con_dato, key=lambda c: c.cambio, default=None)

    @property
    def peor(self) -> Casilla | None:
        return min(self.con_dato, key=lambda c: c.cambio, default=None)


def interpretar(argumento: str, hoy: date) -> tuple[str, int, int]:
    """'btc octubre' -> ('bitcoin', año, 10). Sin mes, el de hoy; sin cripto, ''.

    Un mes que aún no ha llegado este año es el del año pasado.
    """
    partes = argumento.lower().split()
    mes = hoy.month
    año = hoy.year
    if partes and partes[-1] in MESES:
        mes = MESES.index(partes.pop()) + 1
        if mes > hoy.month:
            año -= 1
    if len(partes) > 1:
        raise CalendarioError(f"Escríbelo así: {EJEMPLO}")
    return (a_id(partes[0]) if partes else ""), año, mes


def calcular(dias: list[tuple[date, float]], año: int, mes: int, hoy: date) -> Mes:
    """dias es el último precio de cada día (sale de por_dias), con el mes anterior."""
    precio = dict(dias)
    total = calendar.monthrange(año, mes)[1]
    casillas = []
    for n in range(1, total + 1):
        dia = date(año, mes, n)
        if dia > hoy:
            casillas.append(Casilla(dia, None, futuro=True))
            continue
        ayer = precio.get(dia - timedelta(days=1))
        cambio = None
        if ayer and dia in precio:
            cambio = (precio[dia] / ayer - 1) * 100
            if abs(cambio) < IGUAL:
                cambio = 0.0
        casillas.append(Casilla(dia, cambio))

    # Desde el cierre del día antes del 1; si no lo tengo, desde el primero del mes.
    inicio = date(año, mes, 1) - timedelta(days=1)
    fin = min(date(año, mes, total), hoy)
    del_mes = sorted((d, p) for d, p in dias if inicio <= d <= fin)
    cambio = None
    if len(del_mes) >= 2 and del_mes[0][1]:
        cambio = (del_mes[-1][1] / del_mes[0][1] - 1) * 100
    return Mes(año, mes, casillas, cambio)


def semanas(m: Mes) -> list[list[Casilla | None]]:
    """Filas de lunes a domingo, con None en los huecos de los bordes."""
    filas: list[list[Casilla | None]] = []
    fila: list[Casilla | None] = [None] * m.casillas[0].dia.weekday()
    for c in m.casillas:
        fila.append(c)
        if len(fila) == 7:
            filas.append(fila)
            fila = []
    if fila:
        filas.append(fila + [None] * (7 - len(fila)))
    return filas
