"""Compara precios con los umbrales y decide si hay que avisar."""

import logging
import math
from dataclasses import dataclass

from .config import Watch
from .telegram import escape

logger = logging.getLogger(__name__)

# Estados en los que puede estar una cripto respecto a sus umbrales.
BAJO = "bajo"  # por debajo del minimo
NORMAL = "normal"  # entre los dos umbrales
ALTO = "alto"  # por encima del maximo

SIMBOLOS = {"eur": "€", "usd": "$", "gbp": "£"}

# De menos a mas alto, para dibujar el historico en una linea.
BARRAS = "▁▂▃▄▅▆▇█"


@dataclass(frozen=True)
class Alert:
    """Un aviso que hay que mandar. threshold es el precio que se cruzo."""

    coin_id: str
    price: float
    threshold: float
    estado: str  # BAJO o ALTO
    percent: float | None = None  # variacion, solo en las alertas de %


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

    Nunca repite el mismo aviso: los umbrales fijos solo saltan al CRUZAR,
    y los de variacion solo cuando el precio se mueve otro paso entero.
    """
    alertas = []
    estado_nuevo = dict(estado_previo)

    for watch in watchlist:
        price = prices.get(watch.coin_id)
        if price is None:
            # Sin precio esta vez (fallo de API o id mal escrito).
            # Mantenemos el estado anterior para no avisar de mas luego.
            continue

        if watch.percent is not None:
            aviso, referencia = _revisar_porcentaje(
                price, watch, estado_previo.get(watch.coin_id)
            )
        elif watch.step is not None:
            aviso, referencia = _revisar_variacion(
                price, watch, estado_previo.get(watch.coin_id)
            )
        else:
            aviso, referencia = _revisar_umbral(
                price, watch, estado_previo.get(watch.coin_id)
            )

        estado_nuevo[watch.coin_id] = referencia
        if aviso is not None:
            alertas.append(aviso)

    return alertas, estado_nuevo


def _revisar_umbral(
    price: float, watch: Watch, antes: str | None
) -> tuple[Alert | None, str]:
    """Avisa al cruzar un precio fijo. El estado es la zona: bajo/normal/alto."""
    ahora = clasificar(price, watch)

    if ahora == NORMAL:
        return None, ahora

    # La primera vez no hay estado previo. Avisamos igual: si arrancas
    # con el precio ya fuera de rango, quieres enterarte.
    if antes == ahora:
        logger.debug("%s sigue en '%s', no repetimos aviso", watch.coin_id, ahora)
        return None, ahora

    umbral = watch.min_price if ahora == BAJO else watch.max_price
    return Alert(watch.coin_id, price, umbral, ahora), ahora


def _revisar_variacion(
    price: float, watch: Watch, referencia: str | None
) -> tuple[Alert | None, str]:
    """Avisa cuando el precio cruza un multiplo del paso.

    Con paso 1000 los niveles son 62000, 63000, 64000... Solo avisa al
    pasar uno de esos, no por moverse 1000 desde donde estuviera.
    """
    # Guardamos el ultimo nivel del que avisamos, no el ultimo precio: asi
    # sabemos si el precio ha llegado de verdad al siguiente multiplo.
    ultimo_nivel = _a_float(referencia)

    # El multiplo mas cercano por debajo del precio de ahora. Con paso 1000,
    # 63568 -> 63000; 64000 clavado -> 64000.
    nivel_actual = math.floor(price / watch.step) * watch.step

    # Primera vez: anotamos donde esta y esperamos. Sin nivel anterior no
    # hay forma de saber si acaba de cruzar algo.
    if ultimo_nivel is None:
        logger.debug("%s: nivel de partida %s", watch.coin_id, nivel_actual)
        return None, str(nivel_actual)

    if nivel_actual == ultimo_nivel:
        return None, str(ultimo_nivel)

    subiendo = nivel_actual > ultimo_nivel
    estado = ALTO if subiendo else BAJO

    # Bajando, el multiplo que cruza es el de abajo del nivel anterior:
    # de 63000 a 62800 lo que cruza es el 63000, no el 62000.
    nivel_cruzado = nivel_actual if subiendo else ultimo_nivel

    return Alert(watch.coin_id, price, nivel_cruzado, estado), str(nivel_actual)


def _revisar_porcentaje(
    price: float, watch: Watch, referencia: str | None
) -> tuple[Alert | None, str]:
    """Avisa cuando el precio se aleja un % del ultimo del que avisamos.

    La referencia se mueve con cada aviso, asi que una subida larga avisa
    por tramos (5%, otro 5%...) en vez de una sola vez.
    """
    # El prefijo distingue esta referencia del nivel que guarda el paso fijo:
    # si alguien cambia el formato en el .env, el estado viejo no cuela.
    anterior = _a_float(referencia[1:]) if _es_ref_pct(referencia) else None

    # Primera vez (o formato cambiado): anotamos el precio y esperamos.
    if anterior is None or anterior <= 0:
        logger.debug("%s: precio de partida %s", watch.coin_id, price)
        return None, _ref_pct(price)

    variacion = (price - anterior) / anterior * 100

    if abs(variacion) < watch.percent:
        # Devolvemos la referencia tal cual entro, sin pasarla por float:
        # asi no se reescribe sola en la base de datos cada ciclo.
        return None, referencia

    estado = ALTO if variacion > 0 else BAJO
    return (
        Alert(watch.coin_id, price, anterior, estado, percent=variacion),
        _ref_pct(price),
    )


def _ref_pct(price: float) -> str:
    return f"%{price}"


def _es_ref_pct(valor: str | None) -> bool:
    return bool(valor) and valor.startswith("%")


def _a_float(valor: str | None) -> float | None:
    """Lee el precio de referencia. Ignora los estados viejos (bajo/alto)."""
    if valor is None:
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def formatear(alerta: Alert, currency: str) -> str:
    """Monta el texto del mensaje de Telegram."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(alerta.coin_id.replace("-", " ").title())

    if alerta.estado == BAJO:
        icono, verbo = "🔻", "ha bajado"
    else:
        icono, verbo = "🚀", "ha subido"

    if alerta.percent is not None:
        return (
            f"{icono} <b>{nombre}</b> {verbo} un "
            f"<b>{abs(alerta.percent):.2f}%</b>\n"
            f"De {simbolo}{_num(alerta.threshold)} a "
            f"<b>{simbolo}{_num(alerta.price)}</b>"
        )

    return (
        f"{icono} <b>{nombre}</b> {verbo} de {simbolo}{_num(alerta.threshold)}\n"
        f"Precio actual: <b>{simbolo}{_num(alerta.price)}</b>"
    )


def sparkline(precios: list[float]) -> str:
    """Dibuja los precios como una linea de barritas, del mas viejo al mas nuevo."""
    if len(precios) < 2:
        return ""

    suelo, techo = min(precios), max(precios)
    rango = techo - suelo

    # Todo al mismo precio: una linea plana a media altura, que dividir
    # por un rango de cero reventaria.
    if rango == 0:
        return BARRAS[len(BARRAS) // 2] * len(precios)

    return "".join(
        BARRAS[min(int((p - suelo) / rango * len(BARRAS)), len(BARRAS) - 1)]
        for p in precios
    )


def formatear_varios(alertas: list[Alert], currency: str) -> str:
    """Junta varios avisos en un mensaje. Uno solo se manda tal cual."""
    if len(alertas) == 1:
        return formatear(alertas[0], currency)

    cuerpo = "\n\n".join(formatear(a, currency) for a in alertas)
    return f"<b>{len(alertas)} avisos</b>\n\n{cuerpo}"


def formatear_resumen(
    lineas: list[tuple[str, float, float | None]], currency: str
) -> str:
    """Monta el mensaje de --status. Cada linea es (cripto, precio, variacion)."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["📊 <b>Cómo van tus criptos</b>", ""]

    for coin_id, precio, variacion in lineas:
        nombre = escape(coin_id.replace("-", " ").title())
        linea = f"<b>{nombre}</b>  {simbolo}{_num(precio)}"

        if variacion is None:
            # Recien instalado no hay con que comparar; mejor decirlo que
            # enseñar un 0,00% que parece que no se ha movido.
            linea += "  <i>(sin histórico)</i>"
        else:
            flecha = "🔺" if variacion > 0 else "🔻" if variacion < 0 else "➖"
            linea += f"  {flecha} {variacion:+.2f}%"

        texto.append(linea)

    return "\n".join(texto)


def _num(valor: float) -> str:
    """Formatea el numero segun su tamaño: 55.500 pero 0,3421."""
    if valor >= 1:
        texto = f"{valor:,.2f}"
    else:
        # Las criptos baratas necesitan mas decimales para verse.
        texto = f"{valor:,.4f}"

    # De formato ingles (1,234.56) a español (1.234,56).
    return texto.replace(",", "@").replace(".", ",").replace("@", ".")
