"""Los simbolos de siempre (btc, eth...) traducidos al id de CoinGecko."""

# Con mas de estas en /precio el mensaje ya no cabe en la pantalla del movil.
MAX_VARIAS = 10

# Solo las conocidas: en CoinGecko hay decenas de monedas con el simbolo BTC y
# con la de verdad basta. Para el resto esta /buscar.
IDS = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "xrp": "ripple",
    "bnb": "binancecoin",
    "ada": "cardano",
    "doge": "dogecoin",
    "dot": "polkadot",
    "ltc": "litecoin",
    "link": "chainlink",
    "avax": "avalanche-2",
    "trx": "tron",
    "xlm": "stellar",
    "usdt": "tether",
    "usdc": "usd-coin",
    "shib": "shiba-inu",
    "atom": "cosmos",
    "ton": "the-open-network",
    "uni": "uniswap",
    "xmr": "monero",
    "bch": "bitcoin-cash",
}


def a_id(texto: str) -> str:
    """'BTC' -> 'bitcoin'. Lo que no es un simbolo conocido se queda igual."""
    texto = texto.strip().lower()
    return IDS.get(texto, texto)


def varias(texto: str) -> list[str]:
    """'btc, sol eth' -> ['bitcoin', 'solana', 'ethereum'], sin repetidas."""
    ids = [a_id(t) for t in texto.replace(",", " ").split()]
    return list(dict.fromkeys(ids))
