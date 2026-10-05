"""Alertas de una sola vez: avisan al llegar a un precio y se borran."""

import math
import re
from dataclasses import dataclass

from .simbolos import a_id

# 70.000 es setenta mil, que es como lo escribe uno aqui. 0.5 sigue siendo medio.
_MILES = re.compile(r"[1-9]\d{0,2}(\.\d{3})+")

EJEMPLO = "/alerta bitcoin 70000"
EJEMPLO_RELATIVA = "/alerta bitcoin +10%"

# Con este nombre la alerta es del valor de toda la cartera, no de una cripto.
# Va en la misma tabla, asi no hace falta otra.
CARTERA = "cartera"


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

    return a_id(partes[0]), objetivo


def interpretar_relativa(argumento: str) -> tuple[str, float] | None:
    """'bitcoin +10%' -> ('bitcoin', 10.0). None si no va en porcentaje."""
    partes = argumento.split()
    if len(partes) != 2 or not partes[1].endswith("%"):
        return None

    texto = partes[1][:-1]
    # Sin signo no se sabe si esperar a que suba o a que baje.
    if not texto.startswith(("+", "-")):
        raise PuntualError(f"¿Sube o baja? Pon +{texto}% o -{texto}%")

    porcentaje = numero(texto[1:])
    if porcentaje is None or porcentaje <= 0:
        raise PuntualError(f"'{partes[1]}' no es un porcentaje. Ej: {EJEMPLO_RELATIVA}")
    if texto.startswith("-"):
        porcentaje = -porcentaje
    if porcentaje <= -100:
        raise PuntualError("No puede bajar un 100 % o más, se quedaría en nada.")

    return a_id(partes[0]), porcentaje


def numeros(argumento: str) -> list[int]:
    """'3', '#3' o '2 5, 7' -> los numeros de las alertas, sin repetir."""
    partes = argumento.replace(",", " ").split()
    try:
        ids = [int(p.lstrip("#")) for p in partes]
    except ValueError:
        raise PuntualError("No son números de alerta") from None
    if not ids:
        raise PuntualError("Falta el número de la alerta")
    return list(dict.fromkeys(ids))


def objetivo_relativo(precio: float, porcentaje: float) -> float:
    return precio * (1 + porcentaje / 100)


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
