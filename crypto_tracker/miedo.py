"""/miedo: el indice de miedo y codicia del mercado cripto, de alternative.me."""

from dataclasses import dataclass
from datetime import date, datetime, timezone

import requests

URL = "https://api.alternative.me/fng/"
TIMEOUT = 15

# Hoy, ayer y hace una semana: lo que hace falta para ver hacia donde va.
DIAS = 8

NOMBRES = {
    "extreme fear": ("😱", "Miedo extremo"),
    "fear": ("😟", "Miedo"),
    "neutral": ("😐", "Neutral"),
    "greed": ("😏", "Codicia"),
    "extreme greed": ("🤑", "Codicia extrema"),
}


class MiedoError(Exception):
    """No se pudo leer el indice."""


@dataclass(frozen=True)
class Indice:
    valor: int  # 0 es panico, 100 euforia
    clase: str  # tal cual lo da la API, en ingles
    dia: date


def pedir() -> list[Indice]:
    """Los ultimos dias, el de hoy primero. No gasta cuota de CoinGecko."""
    try:
        respuesta = requests.get(URL, params={"limit": DIAS}, timeout=TIMEOUT)
        respuesta.raise_for_status()
        datos = respuesta.json()
    except requests.RequestException as e:
        raise MiedoError(f"alternative.me no contesta: {e}") from e
    except ValueError as e:
        raise MiedoError("alternative.me devolvio algo que no es JSON") from e
    return leer(datos)


def leer(datos) -> list[Indice]:
    filas = datos.get("data") if isinstance(datos, dict) else None
    lista = []
    for f in filas if isinstance(filas, list) else []:
        if not isinstance(f, dict):
            continue
        # Los numeros vienen como texto: "64", "1791590400".
        try:
            valor = int(f["value"])
            dia = datetime.fromtimestamp(int(f["timestamp"]), timezone.utc).date()
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            continue
        if 0 <= valor <= 100:
            lista.append(Indice(valor, str(f.get("value_classification") or ""), dia))
    return lista


def nombre(indice: Indice) -> tuple[str, str]:
    """(emoji, nombre en español). Si la API se inventa otra clase, va tal cual."""
    return NOMBRES.get(indice.clase.lower(), ("📊", indice.clase or "Sin nombre"))


def hace(lista: list[Indice], dias: int) -> Indice | None:
    """El de hace tantos dias contando desde el primero, si vino."""
    if not lista:
        return None
    buscado = lista[0].dia.toordinal() - dias
    return next((i for i in lista if i.dia.toordinal() == buscado), None)
