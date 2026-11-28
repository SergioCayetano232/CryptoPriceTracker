"""/spread: lo que dice CoinGecko contra lo que dice Binance, ahora mismo."""

from dataclasses import dataclass

from . import estables
from .mensajes.base import SIMBOLOS, _nombre, _num
from .nucleo import binance
from .nucleo.simbolos import MAX_VARIAS, varias

EJEMPLO = "/spread btc eth"

# Por debajo de esto es ruido de que no los miran en el mismo segundo.
IGUALES = 0.05


class SpreadError(Exception):
    """No se entiende qué criptos."""


@dataclass(frozen=True)
class Fila:
    coin_id: str
    coingecko: float
    binance: float

    @property
    def diferencia(self) -> float:
        """En %, lo que Binance va por encima (+) o por debajo (-) de CoinGecko."""
        return (self.binance / self.coingecko - 1) * 100


def interpretar(argumento: str) -> list[str]:
    ids = varias(argumento)
    if len(ids) > MAX_VARIAS:
        raise SpreadError(f"Como mucho {MAX_VARIAS} a la vez.")
    return ids


def calcular(
    coin_ids: list[str], de_coingecko: dict[str, float], de_binance: dict[str, float]
) -> tuple[list[Fila], list[str]]:
    """Las que tienen los dos precios, la más separada primero, y las que no."""
    filas, sueltas = [], []
    for c in coin_ids:
        if de_coingecko.get(c) and de_binance.get(c):
            filas.append(Fila(c, de_coingecko[c], de_binance[c]))
        else:
            sueltas.append(c)
    filas.sort(key=lambda f: abs(f.diferencia), reverse=True)
    return filas, sueltas


def por_que_no(coin_id: str) -> str:
    if coin_id in estables.ESTABLES:
        return "es una estable, contra USDT no dice nada"
    if coin_id not in binance.pares([coin_id]):
        return "no sé cómo se llama en Binance"
    return "no la encuentro ahora mismo"


def texto(filas: list[Fila], sueltas: list[str], currency: str) -> str:
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    lineas = ["⚖️ <b>CoinGecko contra Binance</b>", ""]
    for f in filas:
        dif = f.diferencia
        if abs(dif) < IGUALES:
            marca, cuanto = "✅", "igual"
        else:
            marca = "⚠️" if abs(dif) > binance.MARGEN else "✅"
            cuanto = f"{dif:+.2f}%".replace(".", ",")
        lineas.append(
            f"{marca} <b>{_nombre(f.coin_id)}</b>  {simbolo}{_num(f.coingecko)} · "
            f"{simbolo}{_num(f.binance)}  <i>({cuanto})</i>"
        )
    for c in sueltas:
        lineas.append(f"➖ <b>{_nombre(c)}</b>: {por_que_no(c)}")
    if any(abs(f.diferencia) > binance.MARGEN for f in filas):
        lineas += [
            "",
            f"<i>⚠️ Más de un {binance.MARGEN:g}% suele ser un dato malo, no el "
            "mercado. Si pasa con una que vigilo, no te aviso hasta que cuadre.</i>",
        ]
    # USDT no vale justo un dólar, así que Binance suele salir unas décimas arriba.
    if currency == "eur":
        lineas += ["", "<i>Binance va en USDT; lo paso a euros con su EUR/USDT.</i>"]
    else:
        lineas += [
            "",
            "<i>Binance va en USDT, que no vale justo un dólar: por eso suele "
            "salir unas décimas arriba.</i>",
        ]
    return "\n".join(lineas)
