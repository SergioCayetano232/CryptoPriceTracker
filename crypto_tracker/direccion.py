"""/direccion: vigilar una dirección de bitcoin o de ethereum y avisar si se mueve."""

import json
import re
from dataclasses import asdict, dataclass

import requests

URL = "https://mempool.space/api/address/{}"
VER = "https://mempool.space/address/{}"
# Un nodo público: solo da el saldo, pero contesta igual de rápido con una
# ballena. Blockscout, que da más, con las grandes se quedaba colgado.
URL_ETH = "https://ethereum-rpc.publicnode.com"
VER_ETH = "https://etherscan.io/address/{}"
TIMEOUT = 15

SATS_POR_BTC = 100_000_000
WEI_POR_ETH = 10**18
# Cada una es una consulta por ciclo a mempool.space.
MAXIMO = 10
EJEMPLO = "/direccion bc1q... frío"

# Solo para no mandar cualquier cosa; la que vale de verdad la dice mempool.
_FORMA = re.compile(r"(bc1[a-z0-9]{8,87}|[13][1-9A-HJ-NP-Za-km-z]{25,34})")
_FORMA_ETH = re.compile(r"0x[0-9a-fA-F]{40}")


class DireccionError(Exception):
    """Lo escrito no vale o el servicio no contesta."""


@dataclass(frozen=True)
class Saldo:
    # Se llama sats por las de antes, pero en ethereum son wei.
    sats: int  # con lo que aún está sin confirmar
    txs: int  # en ethereum siempre 0: el nodo no lo da


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
    return bool(_FORMA.fullmatch(texto) or _FORMA_ETH.fullmatch(texto))


def es_eth(direccion: str) -> bool:
    return direccion.lower().startswith("0x")


def coin_id(direccion: str) -> str:
    """De qué cripto es, para buscarle el precio."""
    return "ethereum" if es_eth(direccion) else "bitcoin"


def ver(direccion: str) -> tuple[str, str]:
    """El enlace para verla y el nombre de la web."""
    if es_eth(direccion):
        return VER_ETH.format(direccion), "etherscan.io"
    return VER.format(direccion), "mempool.space"


def a_moneda(direccion: str, unidades: int) -> float:
    """De sats o wei a BTC o ETH."""
    return unidades / (WEI_POR_ETH if es_eth(direccion) else SATS_POR_BTC)


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
    # Las bc1 valen en mayúsculas, pero mempool las guarda en minúsculas. En
    # ethereum las mayúsculas solo son una comprobación: la dirección es la misma.
    if direccion.lower().startswith(("bc1", "0x")):
        direccion = direccion.lower()
    if not es_direccion(direccion):
        raise DireccionError(
            "Eso no parece una dirección de bitcoin ni de ethereum. "
            f"Escríbela así: {EJEMPLO}"
        )
    nombre = " ".join(partes[1:])[:30] or direccion[:8] + "…"
    return "añadir", direccion, nombre


def pedir(direccion: str) -> Saldo:
    if es_eth(direccion):
        return _pedir_eth(direccion)
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


def _pedir_eth(direccion: str) -> Saldo:
    consulta = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getBalance",
        "params": [direccion, "latest"],
    }
    try:
        respuesta = requests.post(URL_ETH, json=consulta, timeout=TIMEOUT)
        respuesta.raise_for_status()
        datos = respuesta.json()
    except requests.RequestException as e:
        raise DireccionError(f"El nodo de ethereum no contesta: {e}") from e
    except ValueError as e:
        raise DireccionError("El nodo de ethereum devolvió algo que no es JSON") from e

    wei = leer_eth(datos)
    if wei is None:
        raise DireccionError("El nodo de ethereum devolvió algo que no entiendo")
    return Saldo(wei, 0)


def leer_eth(datos) -> int | None:
    """El saldo en wei. Viene en hexadecimal: '0x1bc16d674ec80000' es 2 ETH."""
    if not isinstance(datos, dict) or not isinstance(datos.get("result"), str):
        return None
    try:
        return int(datos["result"], 16)
    except ValueError:
        return None


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
    # En ethereum no hay número de transacciones: se ha movido si cambia el saldo.
    if es_eth(antes.direccion):
        return None if ahora.sats == antes.sats else ahora.sats - antes.sats
    if ahora.txs == antes.txs:
        return None
    return ahora.sats - antes.sats
