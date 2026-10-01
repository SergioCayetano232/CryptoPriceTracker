"""Alertas de una sola vez: avisan al llegar a un precio y se borran."""

import math
import re
from dataclasses import dataclass

# 70.000 es setenta mil, que es como lo escribe uno aqui. 0.5 sigue siendo medio.
_MILES = re.compile(r"[1-9]\d{0,2}(\.\d{3})+")

EJEMPLO = "/alerta bitcoin 70000"


class PuntualError(Exception):
    """Lo que escribiste en /alerta no se entiende."""


@dataclass(frozen=True)
class Puntual:
    id: int
    coin_id: str
    objetivo: float
    sube: bool  # True si espera a que suba hasta el objetivo


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 70000' -> ('bitcoin', 70000.0)."""
    partes = argumento.split()
    if len(partes) != 2:
        raise PuntualError(f"Escríbelo así: {EJEMPLO}")

    objetivo = numero(partes[1])
    if objetivo is None or objetivo <= 0:
        raise PuntualError(f"'{partes[1]}' no es un precio. Por ejemplo: {EJEMPLO}")

    return partes[0].lower(), objetivo


def numero(texto: str) -> float | None:
    """Lee 70000, 70.000, 0,35 o 70000€. None si no es un numero."""
    texto = texto.strip().strip("€$£")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif _MILES.fullmatch(texto):
        texto = texto.replace(".", "")

    try:
        valor = float(texto)
    except ValueError:
        return None
    # float() se traga "inf" y "nan", y con eso nunca saltaria
    return valor if math.isfinite(valor) else None


def sube(objetivo: float, precio: float) -> bool:
    """True si hay que esperar a que suba, False si a que baje."""
    if objetivo == precio:
        raise PuntualError("Ya está justo a ese precio ahora mismo.")
    return objetivo > precio


def cumplidas(alertas: list[Puntual], precios: dict[str, float]) -> list[Puntual]:
    """Las que ya han llegado. Pasarse tambien cuenta: entre ciclo y ciclo salta."""
    hechas = []
    for a in alertas:
        precio = precios.get(a.coin_id)
        if precio is None:
            continue
        if (a.sube and precio >= a.objetivo) or (not a.sube and precio <= a.objetivo):
            hechas.append(a)
    return hechas
