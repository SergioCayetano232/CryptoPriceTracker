"""Cliente de la API publica de CoinGecko."""

import logging
import math
import os
import time

import requests

from .maximo import Maximo, leer

logger = logging.getLogger(__name__)

API_URL = "https://api.coingecko.com/api/v3/simple/price"
SEARCH_URL = "https://api.coingecko.com/api/v3/search"
MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"

# Si la API tarda mas que esto, cortamos. Sin timeout una peticion puede
# quedarse colgada para siempre y congelar el bucle entero.
TIMEOUT = 15

# Intentos totales y espera inicial entre ellos. La espera se dobla cada vez
# (2s, 4s): un corte de red de diez segundos ya no nos cuesta el ciclo entero.
INTENTOS = 3
ESPERA_INICIAL = 2

# Peticiones hechas desde la ultima vez que se apuntaron. Aqui no hay base de
# datos, asi que solo se cuentan; main las va guardando.
_hechas = 0

# Variacion en 24 h de cada cripto segun CoinGecko, de la ultima consulta en
# que salio. Va en la misma peticion que el precio, asi que no gasta cuota.
_cambios: dict[str, float] = {}


class CoinGeckoError(Exception):
    """No se pudieron obtener los precios."""

    def __init__(self, mensaje: str, reintentable: bool = False):
        super().__init__(mensaje)
        # Un 429 o un corte de red se pueden reintentar; un id mal escrito no.
        self.reintentable = reintentable


def get_prices(coin_ids: list[str], vs_currency: str = "eur") -> dict[str, float]:
    """Pide los precios actuales y los devuelve como {id: precio}.

    Reintenta los fallos pasajeros (red, 429, 5xx). Las criptos que la API
    no reconozca simplemente no apareceran en el resultado.
    """
    if not coin_ids:
        return {}

    return _con_reintentos(lambda: _pedir_precios(coin_ids, vs_currency))


def buscar(texto: str, maximo: int = 5) -> list[dict]:
    """Busca criptos por nombre o simbolo, las mas probables primero."""
    texto = texto.strip()
    if not texto:
        return []

    data = _con_reintentos(lambda: _pedir(SEARCH_URL, {"query": texto}))
    monedas = data.get("coins", []) if isinstance(data, dict) else []
    return mejores(monedas, texto, maximo)


def maximos(coin_ids: list[str], vs_currency: str = "eur") -> dict[str, Maximo]:
    """El maximo historico de cada una, todas en una sola peticion."""
    if not coin_ids:
        return {}

    params = {"ids": ",".join(coin_ids), "vs_currency": vs_currency}
    return leer(_con_reintentos(lambda: _pedir(MARKETS_URL, params)))


def mejores(monedas: list, texto: str, maximo: int = 5) -> list[dict]:
    """Primero lo que coincide tal cual, luego por tamaño de mercado."""
    buscado = texto.strip().lower()

    def orden(m: dict):
        # Con "btc" salen montones de wrapped y copias; la de verdad es la
        # que tiene ese simbolo exacto y mas capitalizacion.
        exacta = buscado in (
            str(m.get("symbol", "")).lower(),
            str(m.get("name", "")).lower(),
            str(m.get("id", "")).lower(),
        )
        return (not exacta, m.get("market_cap_rank") or float("inf"))

    validas = [m for m in monedas if isinstance(m, dict) and m.get("id")]
    return sorted(validas, key=orden)[:maximo]


def cambio_24h(coin_id: str) -> float | None:
    """Cuanto ha variado en 24 h, en %, segun la ultima consulta. None si no vino."""
    return _cambios.get(coin_id)


def tomar_consultas() -> int:
    """Las peticiones hechas desde la ultima llamada, y pone la cuenta a cero."""
    global _hechas
    hechas, _hechas = _hechas, 0
    return hechas


def _con_reintentos(pedir):
    """Repite la peticion si el fallo es pasajero, esperando el doble cada vez."""
    espera = ESPERA_INICIAL

    for intento in range(1, INTENTOS + 1):
        try:
            return pedir()
        except CoinGeckoError as e:
            if not e.reintentable or intento == INTENTOS:
                raise
            logger.warning(
                "%s. Reintento %d de %d en %ds", e, intento, INTENTOS - 1, espera
            )
            time.sleep(espera)
            espera *= 2

    # Inalcanzable: el bucle o devuelve o relanza.
    raise CoinGeckoError("No se pudieron obtener los precios")


def _pedir_precios(coin_ids: list[str], vs_currency: str) -> dict[str, float]:
    """Una peticion suelta a la API, sin reintentos."""
    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": vs_currency,
        "include_24hr_change": "true",
    }
    return _extract_prices(_pedir(API_URL, params), coin_ids, vs_currency)


def _pedir(url: str, params: dict):
    """GET a CoinGecko traduciendo cada fallo a un CoinGeckoError."""
    global _hechas
    try:
        response = requests.get(
            url, params=params, headers=_cabeceras(), timeout=TIMEOUT
        )
        # Si ha contestado, aunque sea un 429, la cuenta del mes ya ha subido.
        _hechas += 1
        response.raise_for_status()
        data = response.json()
    except requests.Timeout as e:
        raise CoinGeckoError(
            f"CoinGecko tardo mas de {TIMEOUT}s en responder", reintentable=True
        ) from e
    except requests.ConnectionError as e:
        raise CoinGeckoError("Sin conexion con CoinGecko", reintentable=True) from e
    except requests.HTTPError as e:
        status = e.response.status_code
        # 429 = demasiadas peticiones. El plan gratuito limita el ritmo,
        # asi que conviene distinguirlo de un error de verdad.
        if status == 429:
            raise CoinGeckoError(
                "CoinGecko esta limitando las peticiones (429). Sube CHECK_INTERVAL "
                "o pon una COINGECKO_API_KEY en el .env",
                reintentable=True,
            ) from e
        if status == 403:
            raise CoinGeckoError(
                "CoinGecko ha bloqueado la peticion (403). Consigue una clave Demo "
                "gratis en coingecko.com y ponla en COINGECKO_API_KEY del .env"
            ) from e
        # Los 5xx son cosa suya y suelen pasarse solos; los 4xx los tenemos
        # mal nosotros y reintentar no arregla nada.
        raise CoinGeckoError(
            f"CoinGecko respondio con error HTTP {status}", reintentable=status >= 500
        ) from e
    except requests.RequestException as e:
        raise CoinGeckoError(
            f"Fallo la peticion a CoinGecko: {e}", reintentable=True
        ) from e
    except ValueError as e:
        raise CoinGeckoError("CoinGecko devolvio algo que no es JSON") from e

    return data


def _cabeceras() -> dict[str, str]:
    # Se lee en cada peticion y no al importar: asi vale tambien para
    # --buscar, que corre antes de cargar el resto de la configuracion.
    clave = os.getenv("COINGECKO_API_KEY", "").strip()
    return {"x-cg-demo-api-key": clave} if clave else {}


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

        # Si esta vez no viene (a veces llega null), fuera la vieja: mejor sin
        # dato que uno de hace horas.
        cambio = entry.get(f"{vs_currency}_24h_change")
        if isinstance(cambio, (int, float)) and math.isfinite(cambio):
            _cambios[coin_id] = float(cambio)
        else:
            _cambios.pop(coin_id, None)

    faltan = [c for c in coin_ids if c not in prices]
    if faltan:
        logger.warning(
            "CoinGecko no devolvio precio para: %s. Revisa que los ids sean "
            "los suyos (bitcoin, no BTC) y que la moneda '%s' exista.",
            ", ".join(faltan),
            vs_currency,
        )

    return prices
