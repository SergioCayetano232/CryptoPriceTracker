"""/sectores: qué tipo de cripto sube hoy y cuál baja."""

import math
from dataclasses import dataclass

# CoinGecko tiene casi 800 categorías y la mayoría no dicen nada ("Made in
# USA", la cartera de tal fondo...). Estas son las que se entienden, con un
# par de ejemplos para saber de qué va cada una.
SECTORES = {
    "layer-1": ("Blockchains base", "BTC, ETH, SOL"),
    "layer-2": ("Capas sobre Ethereum", "ARB, OP, POL"),
    "decentralized-finance-defi": ("DeFi", "AAVE, UNI, HYPE"),
    "decentralized-exchange": ("Exchanges descentralizados", "UNI, HYPE, CAKE"),
    "lending-borrowing": ("Préstamos", "AAVE, MORPHO"),
    "decentralized-perpetuals": ("Futuros descentralizados", "HYPE, ASTER, JUP"),
    "exchange-based-tokens": ("Tokens de exchanges", "BNB, OKB, LEO"),
    "meme-token": ("Memes", "DOGE, SHIB, PEPE"),
    "artificial-intelligence": ("Inteligencia artificial", "TAO, NEAR, FET"),
    "ai-agents": ("Agentes de IA", "VVV, FET, VIRTUAL"),
    "real-world-assets-rwa": ("Activos reales", "LINK, ONDO, XLM"),
    "privacy-coins": ("Privacidad", "XMR, ZEC"),
    "zero-knowledge-zk": ("Pruebas ZK", "ZEC, POL, STRK"),
    "depin": ("Infraestructura física", "TAO, RENDER, FIL"),
    "oracle": ("Oráculos", "LINK, PYTH"),
    "gaming": ("Videojuegos", "BEAM, GALA, SAND"),
}

# Si CoinGecko cambia los ids y se quedan en nada, mejor no enseñar media lista.
MINIMO = 8


@dataclass(frozen=True)
class Sector:
    nombre: str
    ejemplos: str
    cambio: float  # % en 24 h de lo que valen todas juntas
    capital: float


def leer(datos) -> list[Sector]:
    """De /coins/categories, de la que más sube a la que más baja."""
    lista = []
    for c in datos if isinstance(datos, list) else []:
        if not isinstance(c, dict) or c.get("id") not in SECTORES:
            continue
        cambio = c.get("market_cap_change_24h")
        capital = c.get("market_cap")
        if not (_numero(cambio) and _numero(capital)) or capital <= 0:
            continue
        nombre, ejemplos = SECTORES[c["id"]]
        lista.append(Sector(nombre, ejemplos, float(cambio), float(capital)))
    if len(lista) < MINIMO:
        return []
    return sorted(lista, key=lambda s: -s.cambio)


def _numero(valor) -> bool:
    return isinstance(valor, (int, float)) and math.isfinite(valor)
