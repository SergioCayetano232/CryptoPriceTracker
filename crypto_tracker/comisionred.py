"""/comisionred: lo que cuesta ahora mover bitcoin, de mempool.space."""

from dataclasses import dataclass
from statistics import median

import requests

URL = "https://mempool.space/api/v1/fees/recommended"
SEMANA_URL = "https://mempool.space/api/v1/mining/blocks/fee-rates/1w"
TIMEOUT = 15

# Un envío normal desde un monedero segwit: una entrada y dos salidas (la
# del otro y la vuelta). Si juntas muchas entradas pequeñas, sale más caro.
TAMAÑO = 141
SATS_POR_BTC = 100_000_000

# Por debajo de esto da igual cuándo lo hagas: son céntimos.
REGALADA = 2

# Lo de ahora frente a lo normal de la semana.
BARATA = 0.6
CARA = 1.3

PRISAS = [
    ("fastestFee", "⚡", "En unos 10 min"),
    ("halfHourFee", "🚶", "En media hora"),
    ("hourFee", "🐢", "En una hora"),
    ("economyFee", "💤", "Sin prisa"),
]


EJEMPLO = "/comisionred 5"
QUITAR = "quitar"
_QUITAR = frozenset({"no", "off", "quitar", "quita", "fuera"})
# Más que esto no se ha visto ni en los peores días: será un despiste.
LIMITE_MAXIMO = 1000


class ComisionRedError(Exception):
    """No se pudo leer lo que cobra la red."""


@dataclass(frozen=True)
class Tarifa:
    emoji: str
    nombre: str
    sats_vb: int
    sats: int  # lo que cuesta un envío normal


@dataclass(frozen=True)
class ComisionRed:
    tarifas: list[Tarifa]
    semana: float | None  # lo normal de la semana, en sat/vB
    nivel: str  # regalada, barata, normal, cara o "" si no hay semana


def interpretar(argumento: str) -> int | str | None:
    """'' -> None, verlo. '5' -> avisar al bajar a 5 sat/vB. 'no' -> QUITAR."""
    palabras = argumento.lower().split()
    if not palabras:
        return None
    if palabras == ["no"] or (len(palabras) == 1 and palabras[0] in _QUITAR):
        return QUITAR
    # Vale "5", "5 sat/vB" y "5sat".
    numero = palabras[0].removesuffix("sat/vb").removesuffix("sats").removesuffix("sat")
    if not numero.isdigit() or not 1 <= int(numero) <= LIMITE_MAXIMO:
        raise ComisionRedError(
            f"Dime a cuántos sat/vB te aviso, de 1 a {LIMITE_MAXIMO}. Así: {EJEMPLO}"
        )
    return int(numero)


def pedir_ahora() -> dict:
    """Solo lo de ahora, para el aviso: en cada ciclo no hace falta la semana."""
    return _get(URL)


def pedir() -> tuple[dict, list]:
    """Lo de ahora y lo de la semana. Si falla lo de la semana, va vacío."""
    ahora = _get(URL)
    try:
        semana = _get(SEMANA_URL)
    except ComisionRedError:
        semana = []
    return ahora, semana


def _get(url: str):
    try:
        respuesta = requests.get(url, timeout=TIMEOUT)
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.RequestException as e:
        raise ComisionRedError(f"mempool.space no contesta: {e}") from e
    except ValueError as e:
        raise ComisionRedError("mempool.space devolvió algo que no es JSON") from e


def leer(ahora, semana) -> ComisionRed | None:
    """None si lo de ahora no trae nada que se pueda usar."""
    datos = ahora if isinstance(ahora, dict) else {}
    tarifas = []
    for clave, emoji, nombre in PRISAS:
        valor = datos.get(clave)
        if isinstance(valor, bool) or not isinstance(valor, int | float):
            continue
        if valor > 0:
            tarifas.append(Tarifa(emoji, nombre, round(valor), round(valor * TAMAÑO)))
    if not tarifas:
        return None

    normal = _normal(semana)
    return ComisionRed(tarifas, normal, nivel(tarifas, normal))


def _normal(semana) -> float | None:
    """La mediana de lo que pagó la mitad de cada bloque de la semana."""
    valores = [
        b["avgFee_50"]
        for b in (semana if isinstance(semana, list) else [])
        if isinstance(b, dict) and isinstance(b.get("avgFee_50"), int | float)
    ]
    return median(valores) if valores else None


def media_hora(tarifas: list[Tarifa]) -> Tarifa:
    """La que usa casi todo el mundo. Si no viene, la primera que haya."""
    return next((t for t in tarifas if t.nombre == "En media hora"), tarifas[0])


def toca(c: ComisionRed | None, limite: int) -> bool:
    """Si ya ha bajado a lo que pediste."""
    return c is not None and media_hora(c.tarifas).sats_vb <= limite


def nivel(tarifas: list[Tarifa], normal: float | None) -> str:
    ahora = media_hora(tarifas).sats_vb
    if ahora <= REGALADA:
        return "regalada"
    if not normal:
        return ""
    if ahora <= normal * BARATA:
        return "barata"
    if ahora >= normal * CARA:
        return "cara"
    return "normal"


def en_dinero(sats: int, precio_btc: float) -> float:
    return sats / SATS_POR_BTC * precio_btc
