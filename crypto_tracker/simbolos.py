"""Los simbolos de siempre (btc, eth...) traducidos al id de CoinGecko."""

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
