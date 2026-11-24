"""/profundidad: cuánto dinero hace falta para mover el precio en Binance."""

import math
from dataclasses import dataclass

import requests

URL = "https://api.binance.com/api/v3/depth"
TIMEOUT = 15
# Con 1000 en bitcoin no se llega ni al 0,6%; con 5000, de sobra al 2%.
ORDENES = 5000
TRAMOS = (0.5, 1.0, 2.0)

# Con el doble a un lado que al otro ya se nota hacia dónde aguanta.
DESEQUILIBRIO = 1.5

EJEMPLO = "/profundidad btc"


class ProfundidadError(Exception):
    """No se pudo leer de Binance."""


@dataclass(frozen=True)
class Tramo:
    pct: float
    subir: float  # dólares que hay que comprar para subirlo ese %
    bajar: float  # dólares que hay que vender para bajarlo ese %
    # Si el libro se acaba antes: lo de arriba es lo que hay, y hace falta más.
    subir_corto: bool
    bajar_corto: bool


@dataclass(frozen=True)
class Profundidad:
    par: str
    precio: float  # el punto medio entre la mejor compra y la mejor venta
    tramos: list[Tramo]

    @property
    def mayor(self) -> Tramo:
        return self.tramos[-1]

    @property
    def lado(self) -> str:
        """'compran' si hay mucho más esperando para comprar, 'venden' al revés."""
        t = self.mayor
        if t.bajar >= t.subir * DESEQUILIBRIO:
            return "compran"
        if t.subir >= t.bajar * DESEQUILIBRIO:
            return "venden"
        return ""


def pedir(par: str) -> dict:
    try:
        respuesta = requests.get(
            URL, params={"symbol": par, "limit": ORDENES}, timeout=TIMEOUT
        )
    except requests.RequestException as e:
        raise ProfundidadError(f"Binance no contesta: {e}") from e
    if respuesta.status_code == 400:
        raise ProfundidadError("sin datos")
    if respuesta.status_code == 451:
        raise ProfundidadError("Binance no deja mirarlo desde este país")
    try:
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.RequestException as e:
        raise ProfundidadError(f"Binance no contesta: {e}") from e
    except ValueError as e:
        raise ProfundidadError("Binance devolvió algo que no es JSON") from e


def _ordenes(lista) -> list[tuple[float, float]]:
    ordenes = []
    for o in lista if isinstance(lista, list) else []:
        try:
            precio, cantidad = float(o[0]), float(o[1])
        except (TypeError, ValueError, IndexError):
            continue
        if precio > 0 and cantidad > 0 and math.isfinite(precio * cantidad):
            ordenes.append((precio, cantidad))
    return ordenes


def _hasta(ordenes, dentro) -> tuple[float, bool]:
    """(dólares de las órdenes que caen dentro, si el libro se acaba antes)."""
    total = sum(p * q for p, q in ordenes if dentro(p))
    # Si la última que hay todavía está dentro, no sé cuánto queda detrás.
    return total, not ordenes or dentro(ordenes[-1][0])


def leer(par: str, datos) -> Profundidad | None:
    """None si falta un lado del libro."""
    d = datos if isinstance(datos, dict) else {}
    compras = sorted(_ordenes(d.get("bids")), key=lambda o: -o[0])
    ventas = sorted(_ordenes(d.get("asks")), key=lambda o: o[0])
    if not compras or not ventas:
        return None

    precio = (compras[0][0] + ventas[0][0]) / 2
    tramos = []
    for pct in TRAMOS:
        arriba, abajo = precio * (1 + pct / 100), precio * (1 - pct / 100)
        subir, subir_corto = _hasta(ventas, lambda p, tope=arriba: p <= tope)
        bajar, bajar_corto = _hasta(compras, lambda p, tope=abajo: p >= tope)
        tramos.append(Tramo(pct, subir, bajar, subir_corto, bajar_corto))
    return Profundidad(par, precio, tramos)
