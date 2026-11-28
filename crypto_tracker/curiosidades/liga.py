"""/liga: quién acierta más con /prediccion, entre tú y tus invitados."""

from dataclasses import dataclass
from datetime import datetime

from .prediccion import Prediccion

EJEMPLO = "/liga semana"

_SEMANA = frozenset({"semana", "semanal", "jornada", "domingo", "ultima", "última"})


class LigaError(Exception):
    """Lo que escribiste en /liga no se entiende."""


@dataclass(frozen=True)
class Jugador:
    nombre: str
    yo: bool  # el que pregunta
    predicciones: list[Prediccion]


@dataclass(frozen=True)
class Puesto:
    nombre: str
    yo: bool
    puntos: int
    total: int  # predicciones cerradas
    lado: int  # las que acertó hacia dónde iba
    error_medio: float


def interpretar(argumento: str) -> bool:
    """True es solo la última jornada; False, desde el principio."""
    palabra = argumento.strip().lower()
    if not palabra:
        return False
    if palabra in _SEMANA:
        return True
    raise LigaError(f"A secas es la general. La del último domingo: {EJEMPLO}")


def puntos(p: Prediccion) -> int:
    """Uno por acertar si sube o baja y otro por acercarse más que «se queda igual».

    Así no gana quien más juega con apuestas tímidas ni quien acierta el lado
    quedándose lejísimos.
    """
    return int(p.acierta_lado) + int(p.gana_al_quieto)


def ultima_jornada(jugadores: list[Jugador]) -> datetime | None:
    """El último domingo que se cerró algo, de quien sea."""
    cierres = [
        p.cierre for j in jugadores for p in j.predicciones if p.real is not None
    ]
    return max(cierres) if cierres else None


def clasificar(
    jugadores: list[Jugador], jornada: datetime | None = None
) -> list[Puesto]:
    """De más a menos puntos. Con jornada, solo lo que se cerró ese domingo.

    Quien no tiene ninguna cerrada no sale.
    """
    tabla = []
    for j in jugadores:
        hechas = [
            p
            for p in j.predicciones
            if p.real is not None and (jornada is None or p.cierre == jornada)
        ]
        if not hechas:
            continue
        tabla.append(
            Puesto(
                j.nombre,
                j.yo,
                sum(puntos(p) for p in hechas),
                len(hechas),
                sum(p.acierta_lado for p in hechas),
                sum(p.error for p in hechas) / len(hechas),
            )
        )
    # A igualdad de puntos, quien menos se va; y si no, quien menos ha jugado.
    return sorted(tabla, key=lambda p: (-p.puntos, p.error_medio, p.total, p.nombre))


def posiciones(tabla: list[Puesto]) -> list[int]:
    """El puesto de cada uno: los empatados a puntos comparten número."""
    lugares: list[int] = []
    for i, p in enumerate(tabla):
        if i and p.puntos == tabla[i - 1].puntos:
            lugares.append(lugares[-1])
        else:
            lugares.append(i + 1)
    return lugares
