"""/cada: un comando que te mando yo solo, cada día o un día de la semana."""

from dataclasses import dataclass
from datetime import date, datetime, time

from .config import ConfigError, parse_hora
from .diario import toca_resumen
from .recordar import DIAS, _dia

EJEMPLO = "/cada viernes 20:00 /cartera"
TODOS = {"dia", "día", "dias", "días"}
QUITAR = {"quitar", "no", "borrar"}

# Para que no acabe siendo otro bot dentro del bot.
MAXIMO = 10


class CadaError(Exception):
    """Lo que escribiste en /cada no se entiende."""


@dataclass(frozen=True)
class Programado:
    numero: int
    dia: int | None  # 0 es lunes; None, todos los días
    hora: time
    comando: str
    ultimo: date | None = None

    @property
    def cuando(self) -> str:
        dia = "día" if self.dia is None else DIAS[self.dia]
        return f"cada {dia} a las {self.hora:%H:%M}"


def interpretar(argumento: str) -> tuple[int | None, time, str]:
    """'viernes 20:00 /cartera' -> (4, 20:00, '/cartera')."""
    partes = argumento.split(maxsplit=2)
    if len(partes) != 3 or not partes[2].startswith("/"):
        raise CadaError(f"Escríbelo así: {EJEMPLO} (o /cada dia 9:00 /precio btc)")

    if partes[0].lower() in TODOS:
        dia = None
    else:
        dia = _dia(partes[0])
        if dia is None:
            raise CadaError(f"'{partes[0]}' no es un día. Pon lunes, martes... o dia")

    try:
        hora = parse_hora(partes[1])
    except ConfigError:
        hora = None
    if hora is None:
        raise CadaError(f"'{partes[1]}' no es una hora. Por ejemplo: 20:00")

    comando = partes[2].strip()
    if comando.split()[0].lower().split("@")[0] == "/cada":
        raise CadaError("Un /cada dentro de otro no, que no acabaríamos nunca.")
    # El | es el separador de cómo lo guardo.
    if "|" in comando:
        raise CadaError("El comando no puede llevar |")
    return dia, hora, comando


def para_quitar(argumento: str) -> int | None:
    """'quitar 2' -> 2. None si no es para quitar."""
    partes = argumento.split()
    if len(partes) == 2 and partes[0].lower() in QUITAR:
        try:
            return int(partes[1].lstrip("#"))
        except ValueError:
            raise CadaError("Pon el número que sale en /cada: /cada quitar 1") from None
    return None


def toca(p: Programado, ahora: datetime) -> bool:
    if p.dia is not None and ahora.weekday() != p.dia:
        return False
    return toca_resumen(ahora, p.hora, p.ultimo)


def a_texto(p: Programado) -> str:
    """Como va en ajustes: 'dia|hora|ultimo|comando'. El comando al final."""
    dia = "" if p.dia is None else str(p.dia)
    ultimo = p.ultimo.isoformat() if p.ultimo else ""
    return f"{dia}|{p.hora:%H:%M}|{ultimo}|{p.comando}"


def de_texto(numero: int, texto: str) -> Programado | None:
    """None si está roto: mejor perder uno que tumbar el ciclo."""
    try:
        dia, hora, ultimo, comando = texto.split("|", 3)
        return Programado(
            numero,
            int(dia) if dia else None,
            time.fromisoformat(hora),
            comando,
            date.fromisoformat(ultimo) if ultimo else None,
        )
    except ValueError:
        return None
