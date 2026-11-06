"""/rebalanceo: qué comprar y qué vender para dejar la cartera como digas."""

from dataclasses import dataclass

from .cartera import Valor
from .puntuales import numero
from .simbolos import a_id

EJEMPLO = "/rebalanceo btc 60 eth 40"

# Mover menos del 1% del total no compensa ni la comisión.
QUIETO = 1

# Con 33,3 + 33,3 + 33,3 sale 99,9 y no es culpa de nadie.
HOLGURA = 0.5


class RebalanceoError(Exception):
    """El reparto no se entiende o no suma 100."""


@dataclass(frozen=True)
class Paso:
    coin_id: str
    ahora: float  # lo que vale hoy lo que tienes
    peso: float  # el % que es ahora
    objetivo: float  # el % que quieres
    mover: float  # + comprar, - vender; 0 si ya está
    cantidad: float  # lo mismo en unidades de la cripto, siempre positivo


def interpretar(argumento: str) -> dict[str, float] | None:
    """'btc 60 eth 40' -> {'bitcoin': 60, 'ethereum': 40}. Vacío es a partes iguales."""
    # La coma solo separa al final de un trozo: en 33,3 es un decimal.
    partes = [p.strip(",") for p in argumento.replace(":", " ").split()]
    partes = [p for p in partes if p]
    if not partes:
        return None
    if len(partes) % 2:
        raise RebalanceoError(f"Cada cripto con su %, así: {EJEMPLO}")

    reparto: dict[str, float] = {}
    for nombre, texto in zip(partes[::2], partes[1::2], strict=True):
        pct = numero(texto.rstrip("%"))
        if pct is None or pct < 0:
            raise RebalanceoError(f"No entiendo '{texto}' como un %. Así: {EJEMPLO}")
        coin_id = a_id(nombre)
        if coin_id in reparto:
            raise RebalanceoError(f"Has puesto {nombre} dos veces.")
        reparto[coin_id] = pct

    suma = sum(reparto.values())
    if abs(suma - 100) > HOLGURA:
        texto = f"{suma:g}".replace(".", ",")
        raise RebalanceoError(f"Tiene que sumar 100% y suma {texto}%.")
    return reparto


def iguales(coin_ids: list[str]) -> dict[str, float]:
    return {c: 100 / len(coin_ids) for c in coin_ids}


def calcular(
    valores: list[Valor], reparto: dict[str, float], precios: dict[str, float]
) -> list[Paso]:
    """Primero las ventas, que dan el dinero para las compras.

    Las que tienes y no están en el reparto van a 0: venderlas enteras.
    precios tiene que traer también las que no tienes y quieres comprar.
    """
    total = sum(v.valor for v in valores)
    if total <= 0:
        return []
    tienes = {v.coin_id: v.valor for v in valores}

    pasos = []
    for coin_id in dict.fromkeys([*tienes, *reparto]):
        ahora = tienes.get(coin_id, 0.0)
        objetivo = reparto.get(coin_id, 0.0)
        mover = total * objetivo / 100 - ahora
        if abs(mover) < total * QUIETO / 100:
            mover = 0.0
        # Vender todo es vender todo, no lo que salga de la cuenta con decimales.
        if not objetivo:
            mover = -ahora
        pasos.append(
            Paso(
                coin_id,
                ahora,
                ahora / total * 100,
                objetivo,
                mover,
                abs(mover) / precios[coin_id],
            )
        )

    return sorted(pasos, key=lambda p: (p.mover >= 0, -abs(p.mover)))
