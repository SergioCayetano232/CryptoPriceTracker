"""/direccion: vigilar una dirección de bitcoin y avisar cuando se mueve."""

import json
import re
from dataclasses import asdict, dataclass

import requests

URL = "https://mempool.space/api/address/{}"
VER = "https://mempool.space/address/{}"
TIMEOUT = 15

SATS_POR_BTC = 100_000_000
# Cada una es una consulta por ciclo a mempool.space.
MAXIMO = 10
EJEMPLO = "/direccion bc1q... frío"

# Solo para no mandar cualquier cosa; la que vale de verdad la dice mempool.
_FORMA = re.compile(r"(bc1[a-z0-9]{8,87}|[13][1-9A-HJ-NP-Za-km-z]{25,34})")


class DireccionError(Exception):
    """Lo escrito no vale o mempool.space no contesta."""


@dataclass(frozen=True)
class Saldo:
    sats: int  # con lo que aún está sin confirmar
    txs: int


@dataclass(frozen=True)
class Vigilada:
    direccion: str
    nombre: str
    sats: int
    txs: int

    def guardar(self) -> str:
        datos = asdict(self)
        del datos["direccion"]
        return json.dumps(datos, ensure_ascii=False)


def es_direccion(texto: str) -> bool:
    return bool(_FORMA.fullmatch(texto))


def interpretar(argumento: str) -> tuple[str, str, str]:
    """('ver', '', '') a secas, ('añadir', dirección, nombre) o
    ('quitar', dirección o nombre, '')."""
    partes = argumento.split()
    if not partes:
        return "ver", "", ""
    if partes[0].lower() in ("quitar", "borrar", "-"):
        if len(partes) < 2:
            raise DireccionError("¿Cuál? Por ejemplo: /direccion quitar frío")
        return "quitar", " ".join(partes[1:]), ""

    direccion = partes[0]
    # Las bc1 valen en mayúsculas, pero mempool las guarda en minúsculas.
    if direccion.lower().startswith("bc1"):
        direccion = direccion.lower()
    if not es_direccion(direccion):
        raise DireccionError(
            f"Eso no parece una dirección de bitcoin. Escríbela así: {EJEMPLO}"
        )
    nombre = " ".join(partes[1:])[:30] or direccion[:8] + "…"
    return "añadir", direccion, nombre


def pedir(direccion: str) -> Saldo:
    try:
        respuesta = requests.get(URL.format(direccion), timeout=TIMEOUT)
    except requests.RequestException as e:
        raise DireccionError(f"mempool.space no contesta: {e}") from e
    if respuesta.status_code == 400:
        raise DireccionError("mempool.space dice que esa dirección no existe")
    try:
        respuesta.raise_for_status()
        datos = respuesta.json()
    except requests.RequestException as e:
        raise DireccionError(f"mempool.space no contesta: {e}") from e
    except ValueError as e:
        raise DireccionError("mempool.space devolvió algo que no es JSON") from e

    saldo = leer(datos)
    if saldo is None:
        raise DireccionError("mempool.space devolvió algo que no entiendo")
    return saldo


def leer(datos) -> Saldo | None:
    if not isinstance(datos, dict):
        return None
    sats = txs = 0
    # chain es lo confirmado y mempool lo que está esperando: así avisa en
    # cuanto sale, sin esperar al bloque, y al confirmarse no repite.
    for parte in ("chain_stats", "mempool_stats"):
        s = datos.get(parte)
        if not isinstance(s, dict):
            return None
        try:
            sats += int(s["funded_txo_sum"]) - int(s["spent_txo_sum"])
            txs += int(s["tx_count"])
        except (KeyError, TypeError, ValueError):
            return None
    return Saldo(sats, txs)


def cargar(direccion: str, valor: str) -> Vigilada | None:
    """De lo guardado en ajustes. None si está roto."""
    try:
        datos = json.loads(valor)
        return Vigilada(
            direccion, str(datos["nombre"]), int(datos["sats"]), int(datos["txs"])
        )
    except (ValueError, TypeError, KeyError):
        return None


def buscar(vigiladas: list[Vigilada], texto: str) -> Vigilada | None:
    """Por la dirección entera o por el nombre, sin mirar mayúsculas."""
    texto = texto.strip().lower()
    return next(
        (v for v in vigiladas if texto in (v.direccion.lower(), v.nombre.lower())),
        None,
    )


def movida(antes: Vigilada, ahora: Saldo) -> int | None:
    """Lo que ha entrado (o salido, en negativo) en sats. None si no se ha movido."""
    if ahora.txs == antes.txs:
        return None
    return ahora.sats - antes.sats


def a_btc(sats: int) -> float:
    return sats / SATS_POR_BTC
