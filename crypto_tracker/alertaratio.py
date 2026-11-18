"""/alerta eth/btc 0.05: avisa una vez cuando una valga eso en la otra."""

from dataclasses import dataclass

from .puntuales import numero
from .simbolos import a_id

EJEMPLO = "/alerta eth/btc 0.05"
QUITAR = {"no", "quitar", "off"}


class AlertaRatioError(Exception):
    """Lo que escribiste en /alerta eth/btc no se entiende."""


@dataclass(frozen=True)
class AlertaRatio:
    coin_id: str
    contra: str
    objetivo: float
    sube: bool


def es_ratio(argumento: str) -> bool:
    primera = argumento.split()[0] if argumento.split() else ""
    return "/" in primera.strip("/")


def interpretar(argumento: str) -> tuple[str, str, str | None]:
    """'eth/btc 0.05' -> ('ethereum', 'bitcoin', '0.05'). Sin nada detrás, None."""
    partes = argumento.split()
    if len(partes) > 2:
        raise AlertaRatioError(f"Escríbelo así: {EJEMPLO}")
    una, _, otra = partes[0].partition("/")
    if not una or not otra or "/" in otra:
        raise AlertaRatioError(f"Escríbelo así: {EJEMPLO}")
    coin_id, contra = a_id(una), a_id(otra)
    if coin_id == contra:
        raise AlertaRatioError("Son la misma: siempre vale 1.")
    return coin_id, contra, partes[1] if len(partes) == 2 else None


def es_quitar(texto: str | None) -> bool:
    return texto is not None and texto.lower() in QUITAR


def objetivo(texto: str) -> float:
    valor = numero(texto)
    if valor is None or valor <= 0:
        raise AlertaRatioError(f"'{texto}' no es un número. Por ejemplo: {EJEMPLO}")
    return valor


def crear(coin_id: str, contra: str, valor: float, ahora: float) -> AlertaRatio:
    if valor == ahora:
        raise AlertaRatioError("Ya vale justo eso ahora mismo.")
    return AlertaRatio(coin_id, contra, valor, valor > ahora)


def cumplida(a: AlertaRatio, ahora: float) -> bool:
    # Pasarse también cuenta: entre ciclo y ciclo puede saltárselo.
    return ahora >= a.objetivo if a.sube else ahora <= a.objetivo


def criptos(lista: list[AlertaRatio]) -> list[str]:
    """Las que hace falta consultar en cada vuelta."""
    return list(dict.fromkeys(c for a in lista for c in (a.coin_id, a.contra)))
