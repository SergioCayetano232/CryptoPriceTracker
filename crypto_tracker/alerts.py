"""Compara precios con los umbrales y decide si hay que avisar."""

import logging
from dataclasses import dataclass

from .config import Watch
from .telegram import escape

logger = logging.getLogger(__name__)

# Estados en los que puede estar una cripto respecto a sus umbrales.
BAJO = "bajo"      # por debajo del minimo
NORMAL = "normal"  # entre los dos umbrales
ALTO = "alto"      # por encima del maximo

SIMBOLOS = {"eur": "€", "usd": "$", "gbp": "£"}


@dataclass(frozen=True)
class Alert:
    """Un aviso que hay que mandar."""

    coin_id: str
    price: float
    threshold: float
    estado: str  # BAJO o ALTO


def clasificar(price: float, watch: Watch) -> str:
    """Mira en que zona cae el precio segun los umbrales."""
    if watch.min_price is not None and price < watch.min_price:
        return BAJO
    if watch.max_price is not None and price > watch.max_price:
        return ALTO
    return NORMAL


def revisar(
    prices: dict[str, float],
    watchlist: list[Watch],
    estado_previo: dict[str, str],
) -> tuple[list[Alert], dict[str, str]]:
    """Decide que alertas tocan y devuelve el estado nuevo.

    Solo avisa cuando el precio CRUZA un umbral, no mientras siga fuera.
    Si no, con un precio bajo tendrias un mensaje cada pocos minutos.
    """
    alertas = []
    estado_nuevo = dict(estado_previo)

    for watch in watchlist:
        price = prices.get(watch.coin_id)
        if price is None:
            # Sin precio esta vez (fallo de API o id mal escrito).
            # Mantenemos el estado anterior para no avisar de mas luego.
            continue

        antes = estado_previo.get(watch.coin_id)
        ahora = clasificar(price, watch)
        estado_nuevo[watch.coin_id] = ahora

        if ahora == NORMAL:
            continue

        # La primera vez no hay estado previo. Avisamos igual: si arrancas
        # con el precio ya fuera de rango, quieres enterarte.
        if antes == ahora:
            logger.debug("%s sigue en '%s', no repetimos aviso", watch.coin_id, ahora)
            continue

        umbral = watch.min_price if ahora == BAJO else watch.max_price
        alertas.append(Alert(watch.coin_id, price, umbral, ahora))

    return alertas, estado_nuevo


def formatear(alerta: Alert, currency: str) -> str:
    """Monta el texto del mensaje de Telegram."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(alerta.coin_id.replace("-", " ").title())

    if alerta.estado == BAJO:
        icono, verbo = "🔻", "ha bajado de"
    else:
        icono, verbo = "🚀", "ha subido de"

    return (
        f"{icono} <b>{nombre}</b> {verbo} {simbolo}{_num(alerta.threshold)}\n"
        f"Precio actual: <b>{simbolo}{_num(alerta.price)}</b>"
    )


def _num(valor: float) -> str:
    """Formatea el numero segun su tamaño: 55.500 pero 0,3421."""
    if valor >= 1:
        texto = f"{valor:,.2f}"
    else:
        # Las criptos baratas necesitan mas decimales para verse.
        texto = f"{valor:,.4f}"

    # De formato ingles (1,234.56) a español (1.234,56).
    return texto.replace(",", "@").replace(".", ",").replace("@", ".")
