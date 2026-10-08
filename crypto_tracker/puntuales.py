"""Alertas de una sola vez: avisan al llegar a un precio y se borran."""

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from .periodo import PeriodoError, es_tramo, leer
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
    caduca: datetime | None = None  # None, las de antes y las que no lo pidieron


def separar_caducidad(argumento: str) -> tuple[str, float | None]:
    """'bitcoin 70000 7d' -> ('bitcoin 70000', 168). Sin caducidad, None."""
    partes = argumento.split()
    # Con dos partes no: "bitcoin 70000" tambien pareceria un tramo.
    if len(partes) != 3 or not es_tramo(partes[2]):
        return argumento, None
    try:
        horas = leer(partes[2])
    except PeriodoError as e:
        raise PuntualError(str(e)) from None
    return " ".join(partes[:2]), horas


def caducidad(ahora: datetime, horas: float | None) -> datetime | None:
    return ahora + timedelta(hours=horas) if horas else None


def caducadas(alertas: list[Puntual], ahora: datetime) -> list[Puntual]:
    return [a for a in alertas if a.caduca and a.caduca <= ahora]


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


def ejemplo(precio: float) -> str:
    """Un precio redondo algo por encima del de ahora, para poner de ejemplo."""
    # Dos cifras: con mas ya no parece un numero que escribirias tu.
    paso = 10 ** (math.floor(math.log10(precio * 1.1)) - 1)
    redondo = math.floor(precio * 1.1 / paso) * paso
    decimales = max(0, -round(math.log10(paso)))
    # Con coma decimal, como lo escribiria uno aqui.
    return f"{redondo:.{decimales}f}".replace(".", ",")


def numero(texto: str) -> float | None:
    """Lee 70000, 70.000, 0,35, 70000€ o 70k. None si no es un numero."""
    texto = texto.strip().strip("€$£")
    por = 1
    if texto[-1:] in ("k", "K"):
        texto, por = texto[:-1], 1000
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif _MILES.fullmatch(texto):
        texto = texto.replace(".", "")

    try:
        valor = float(texto) * por
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
