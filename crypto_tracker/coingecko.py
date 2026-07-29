"""Cliente de la API publica de CoinGecko (no hace falta API key)."""

import logging

import requests

logger = logging.getLogger(__name__)

API_URL = "https://api.coingecko.com/api/v3/simple/price"

# Si la API tarda mas que esto, cortamos. Sin timeout una peticion puede
# quedarse colgada para siempre y congelar el bucle entero.
TIMEOUT = 15


class CoinGeckoError(Exception):
    """No se pudieron obtener los precios."""


def get_prices(coin_ids: list[str], vs_currency: str = "eur") -> dict[str, float]:
    """Pide los precios actuales y los devuelve como {id: precio}.

    Las criptos que la API no reconozca simplemente no apareceran en el
    resultado. Lanza CoinGeckoError si la peticion falla del todo.
    """
    if not coin_ids:
        return {}

    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": vs_currency,
    }

    try:
        response = requests.get(API_URL, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.Timeout as e:
        raise CoinGeckoError(f"CoinGecko tardo mas de {TIMEOUT}s en responder") from e
    except requests.ConnectionError as e:
        raise CoinGeckoError("Sin conexion con CoinGecko") from e
    except requests.HTTPError as e:
        status = e.response.status_code
        # 429 = demasiadas peticiones. El plan gratuito limita el ritmo,
        # asi que conviene distinguirlo de un error de verdad.
        if status == 429:
            raise CoinGeckoError(
                "CoinGecko esta limitando las peticiones (429), sube CHECK_INTERVAL"
            ) from e
        raise CoinGeckoError(f"CoinGecko respondio con error HTTP {status}") from e
    except requests.RequestException as e:
        raise CoinGeckoError(f"Fallo la peticion a CoinGecko: {e}") from e
    except ValueError as e:
        raise CoinGeckoError("CoinGecko devolvio algo que no es JSON") from e

    return _extract_prices(data, coin_ids, vs_currency)


def _extract_prices(
    data: dict, coin_ids: list[str], vs_currency: str
) -> dict[str, float]:
    """Saca los precios del JSON y avisa de los ids que no vinieron.

    Ojo: un id mal escrito no da error en la API, devuelve {} y un 200.
    Por eso lo comprobamos aqui.
    """
    prices = {}

    for coin_id in coin_ids:
        entry = data.get(coin_id)
        if not isinstance(entry, dict) or vs_currency not in entry:
            continue

        try:
            prices[coin_id] = float(entry[vs_currency])
        except (TypeError, ValueError):
            logger.warning("Precio raro para %s: %r", coin_id, entry[vs_currency])

    faltan = [c for c in coin_ids if c not in prices]
    if faltan:
        logger.warning(
            "CoinGecko no devolvio precio para: %s. Revisa que los ids sean "
            "los suyos (bitcoin, no BTC) y que la moneda '%s' exista.",
            ", ".join(faltan),
            vs_currency,
        )

    return prices
