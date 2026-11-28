"""/altseason: cuántas de las grandes le ganan a bitcoin en el último mes."""

import math
from dataclasses import dataclass

# Pido 100 porque, quitando estables y envoltorios, se queda en unas 70.
PEDIR = 100
CUANTAS = 50
DIAS = 30
# El índice de siempre usa 90 días, pero CoinGecko solo da 30 o 200 en esta
# consulta, así que es la versión de un mes y salta antes.
ALTCOINS = 75
BITCOIN = 25
DESTACADAS = 3
EJEMPLO = "/altseason"

# Las que cuestan lo mismo que otra y solo la copian.
_NO_CUENTAN = {"dai", "eurc", "xaut", "paxg"}
_POR_NOMBRE = (
    "wrapped",
    "staked",
    "bridged",
    # Fondos de letras y similares, que valen un dólar y poco más.
    "fund",
    "treasur",
    "t-bill",
    "money market",
    "duration",
    "yield",
    "dollar",
)


@dataclass(frozen=True)
class Moneda:
    coin_id: str
    simbolo: str
    cambio: float  # % en 30 días


@dataclass(frozen=True)
class Temporada:
    bitcoin: float  # lo que ha hecho bitcoin en 30 días
    monedas: list[Moneda]  # las que cuentan, en orden de tamaño

    @property
    def ganan(self) -> list[Moneda]:
        return [m for m in self.monedas if m.cambio > self.bitcoin]

    @property
    def indice(self) -> int:
        return round(100 * len(self.ganan) / len(self.monedas))

    @property
    def toca(self) -> str:
        """'altcoins', 'bitcoin' o '' si no es ni una ni otra."""
        if self.indice >= ALTCOINS:
            return "altcoins"
        return "bitcoin" if self.indice <= BITCOIN else ""

    def mejores(self) -> list[Moneda]:
        return sorted(self.monedas, key=lambda m: -m.cambio)[:DESTACADAS]

    def peores(self) -> list[Moneda]:
        return sorted(self.monedas, key=lambda m: m.cambio)[:DESTACADAS]


def cuenta(simbolo: str, nombre: str, precio: float, cambio: float) -> bool:
    """Si entra en la cuenta: fuera estables, oro, fondos y copias de otra."""
    s, n = simbolo.lower(), nombre.lower()
    if "usd" in s or s in _NO_CUENTAN:
        return False
    if any(p in n for p in _POR_NOMBRE):
        return False
    # Un dólar y pico que en un mes casi ni se mueve: un fondo con otro nombre.
    if 0.9 <= precio <= 1.25 and abs(cambio) < 3:
        return False
    # rETH, solvBTC, jitoSOL... no las pilla el nombre pero van pegadas a la suya.
    return not (len(s) > 3 and s.endswith(("btc", "eth", "sol")))


def leer(datos) -> Temporada | None:
    """De /coins/markets en dólares; None si falta bitcoin o hay muy pocas."""
    bitcoin = None
    monedas = []
    for m in datos if isinstance(datos, list) else []:
        if not isinstance(m, dict) or not m.get("id"):
            continue
        cambio = m.get(f"price_change_percentage_{DIAS}d_in_currency")
        if not isinstance(cambio, (int, float)) or not math.isfinite(cambio):
            continue
        if m["id"] == "bitcoin":
            bitcoin = float(cambio)
            continue
        simbolo = str(m.get("symbol") or "")
        precio = m.get("current_price")
        if not isinstance(precio, (int, float)):
            continue
        if cuenta(simbolo, str(m.get("name") or ""), precio, cambio):
            monedas.append(Moneda(m["id"], simbolo.upper(), float(cambio)))

    # Con menos de la mitad el porcentaje ya no dice gran cosa.
    if bitcoin is None or len(monedas) < CUANTAS // 2:
        return None
    return Temporada(bitcoin, monedas[:CUANTAS])
