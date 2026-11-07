"""/recordar: un aviso cada semana de tu compra periódica, con botón para apuntarla."""

import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time

from .diario import toca_resumen
from .puntuales import numero
from .simbolos import a_id

EJEMPLO = "/recordar lunes 50 btc"

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

# Para quien no tenga /horario puesto: a primera hora, antes de abrir el exchange.
HORA = time(9, 0)

QUITAR = {"no", "quitar", "off", "nunca"}


class RecordarError(Exception):
    """Lo que escribiste en /recordar no se entiende."""


@dataclass(frozen=True)
class Recordatorio:
    coin_id: str
    dia: int  # 0 es lunes, como weekday()
    importe: float
    ultimo: date | None = None  # el último día que te lo mandé

    @property
    def nombre_dia(self) -> str:
        return DIAS[self.dia]


def _sin_tildes(texto: str) -> str:
    sin = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sin if unicodedata.category(c) != "Mn")


def _dia(texto: str) -> int | None:
    limpio = _sin_tildes(texto.lower())
    for i, dia in enumerate(DIAS):
        if _sin_tildes(dia) == limpio:
            return i
    return None


def para_quitar(argumento: str) -> str | None:
    """'btc no' o 'quitar btc' -> 'bitcoin'. None si no es para quitar."""
    partes = argumento.split()
    if len(partes) != 2:
        return None
    if partes[1].lower() in QUITAR:
        return a_id(partes[0])
    if partes[0].lower() in QUITAR:
        return a_id(partes[1])
    return None


def interpretar(argumento: str) -> Recordatorio:
    """'lunes 50 btc' -> Recordatorio('bitcoin', 0, 50)."""
    partes = argumento.split()
    if len(partes) != 3:
        raise RecordarError(f"Escríbelo así: {EJEMPLO} (el día, cuánto y de cuál)")

    dia = _dia(partes[0])
    if dia is None:
        raise RecordarError(f"'{partes[0]}' no es un día de la semana. Ej: {EJEMPLO}")
    importe = numero(partes[1])
    if importe is None or importe <= 0:
        raise RecordarError(
            f"'{partes[1]}' no es una cantidad de dinero. Ej: {EJEMPLO}"
        )
    return Recordatorio(a_id(partes[2]), dia, importe)


def toca(r: Recordatorio, ahora: datetime, hora: time | None) -> bool:
    return ahora.weekday() == r.dia and toca_resumen(ahora, hora or HORA, r.ultimo)


def comando_compra(r: Recordatorio, precio: float) -> str:
    """El /compra del botón, con lo que te daría el importe al precio de ahora."""
    # Con coma: numero() leería "1.234" como mil doscientos.
    cantidad = f"{r.importe / precio:.8f}".rstrip("0").rstrip(".").replace(".", ",")
    importe = f"{r.importe:g}".replace(".", ",")
    return f"/compra {r.coin_id} {cantidad} {importe}"


def a_texto(r: Recordatorio) -> str:
    """Como va en la tabla de ajustes: 'dia|importe|ultimo'."""
    ultimo = r.ultimo.isoformat() if r.ultimo else ""
    return f"{r.dia}|{r.importe!r}|{ultimo}"


def de_texto(coin_id: str, texto: str) -> Recordatorio | None:
    """None si está roto: mejor perder uno que tumbar el ciclo."""
    try:
        dia, importe, ultimo = texto.split("|")
        return Recordatorio(
            coin_id,
            int(dia),
            float(importe),
            date.fromisoformat(ultimo) if ultimo else None,
        )
    except ValueError:
        return None
