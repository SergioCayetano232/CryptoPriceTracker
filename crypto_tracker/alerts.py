"""Compara precios con los umbrales y decide si hay que avisar."""

import logging
import math
from dataclasses import dataclass
from datetime import datetime

from .cartera import Valor
from .config import Posicion, Watch
from .movimientos import texto_cantidad
from .periodo import nombre as nombre_periodo
from .puntuales import Puntual
from .semanal import Semana
from .telegram import escape

logger = logging.getLogger(__name__)

# Estados en los que puede estar una cripto respecto a sus umbrales.
BAJO = "bajo"  # por debajo del minimo
NORMAL = "normal"  # entre los dos umbrales
ALTO = "alto"  # por encima del maximo

SIMBOLOS = {"eur": "€", "usd": "$", "gbp": "£"}

# El plan gratis de CoinGecko pide citarles, con enlace, junto a los datos.
# La frase tiene que ser una de las suyas, por eso va en ingles.
FUENTE = '<i>Price data by <a href="https://www.coingecko.com">CoinGecko</a></i>'

# De menos a mas alto, para dibujar el historico en una linea.
BARRAS = "▁▂▃▄▅▆▇█"

# Mas barritas que esto y en el movil la linea salta a la siguiente.
BARRAS_MOVIL = 24


@dataclass(frozen=True)
class Alert:
    """Un aviso que hay que mandar. threshold es el precio que se cruzo."""

    coin_id: str
    price: float
    threshold: float
    estado: str  # BAJO o ALTO
    percent: float | None = None  # variacion, solo en las alertas de %
    minutos: int | None = None  # solo en los movimientos bruscos
    puntual: bool = False  # de /alerta, se borra al avisar
    variacion_24h: float | None = None  # None si aun no hay historico de un dia


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

    if alerta.minutos is not None:
        verbo = "ha caído" if alerta.estado == BAJO else "ha subido"
        texto = (
            f"⚡ <b>{nombre}</b> {verbo} un <b>{abs(alerta.percent):.2f}%</b> "
            f"en menos de {_minutos(alerta.minutos)}\n"
            f"De {simbolo}{_num(alerta.threshold)} a "
            f"<b>{simbolo}{_num(alerta.price)}</b>"
        )
    elif alerta.percent is not None:
        texto = (
            f"{icono} <b>{nombre}</b> {verbo} un "
            f"<b>{abs(alerta.percent):.2f}%</b>\n"
            f"De {simbolo}{_num(alerta.threshold)} a "
            f"<b>{simbolo}{_num(alerta.price)}</b>"
        )
    else:
        texto = (
            f"{icono} <b>{nombre}</b> {verbo} de {simbolo}{_num(alerta.threshold)}\n"
            f"Precio actual: <b>{simbolo}{_num(alerta.price)}</b>"
        )

    # Cruzar 64.000 no es lo mismo si viene de subir un 1% que un 15%.
    if alerta.variacion_24h is not None:
        v = alerta.variacion_24h
        texto += f"\n<i>En 24 h: {_flecha(v)} {v:+.2f}%</i>"
    if alerta.puntual:
        texto += "\n<i>Era tu /alerta, ya la he quitado.</i>"
    return texto


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


def con_fuente(texto: str) -> str:
    return f"{texto}\n\n{FUENTE}"


def formatear_varios(alertas: list[Alert], currency: str) -> str:
    """Junta varios avisos en un mensaje. Uno solo se manda tal cual."""
    if len(alertas) == 1:
        return formatear(alertas[0], currency)

    cuerpo = "\n\n".join(formatear(a, currency) for a in alertas)
    return f"<b>{len(alertas)} avisos</b>\n\n{cuerpo}"


def formatear_resumen(
    lineas: list[tuple[str, float, float | None]],
    currency: str,
    titulo: str = "📊 <b>Cómo van tus criptos</b>",
    proximos: dict[str, tuple[float | None, float | None]] | None = None,
) -> str:
    """Monta el mensaje de --status. Cada linea es (cripto, precio, variacion).

    proximos son los precios (arriba, abajo) del siguiente aviso de cada una.
    """
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [titulo, ""]

    for coin_id, precio, variacion in lineas:
        nombre = escape(coin_id.replace("-", " ").title())
        linea = f"<b>{nombre}</b>  {simbolo}{_num(precio)}"

        if variacion is None:
            # Recien instalado no hay con que comparar; mejor decirlo que
            # enseñar un 0,00% que parece que no se ha movido.
            linea += "  <i>(sin histórico)</i>"
        else:
            linea += f"  {_flecha(variacion)} {variacion:+.2f}%"

        texto.append(linea)
        siguiente = _siguiente(
            precio, *(proximos or {}).get(coin_id, (None, None)), simbolo
        )
        if siguiente:
            texto.append(f"   <i>{siguiente}</i>")

    return "\n".join(texto)


def formatear_historico(
    coin_id: str,
    precios: list[float],
    currency: str,
    horas: float,
    con_linea: bool = True,
    desde: datetime | None = None,
) -> str:
    """Mensaje de /historico. Los precios van del mas viejo al mas nuevo.

    desde va solo si faltan datos del principio, para no vender un tramo entero.
    """
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    ahora = precios[-1]
    variacion = (ahora - precios[0]) / precios[0] * 100 if precios[0] else 0.0

    # Con la imagen al lado, las barritas sobran.
    linea = ""
    if con_linea:
        linea = f"<code>{sparkline(muestrear(precios, BARRAS_MOVIL))}</code>\n"

    texto = (
        f"📈 <b>{nombre}</b>, {nombre_periodo(horas)}\n"
        f"{linea}\n"
        f"Ahora <b>{simbolo}{_num(ahora)}</b>  {_flecha(variacion)} {variacion:+.2f}%\n"
        f"Máximo {simbolo}{_num(max(precios))}\n"
        f"Mínimo {simbolo}{_num(min(precios))}"
    )
    if desde is not None:
        cuando = desde.astimezone()
        texto += f"\n<i>Solo tengo precios desde el {cuando:%d/%m a las %H:%M}.</i>"
    return texto


def formatear_cartera(
    valores: list[Valor], total: Valor, faltan: list[str], currency: str
) -> str:
    """Bloque de la cartera para el resumen: cada cripto y el total."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["💼 <b>Tu cartera</b>"]

    for v in valores:
        nombre = escape(v.coin_id.replace("-", " ").title())
        linea = f"<b>{nombre}</b>  {simbolo}{_num(v.valor)}"
        if v.porcentaje is not None:
            linea += f"  {_flecha(v.porcentaje)} {v.porcentaje:+.2f}%"
        texto.append(linea)

    linea = f"\nTotal <b>{simbolo}{_num(total.valor)}</b>"
    if total.porcentaje is not None:
        signo = "+" if total.ganancia >= 0 else "-"
        linea += (
            f"  {_flecha(total.porcentaje)} {total.porcentaje:+.2f}% "
            f"({signo}{simbolo}{_num(abs(total.ganancia))})"
        )
    texto.append(linea)

    if faltan:
        # Mejor decir que el total esta cojo que dar uno que parezca completo.
        nombres = ", ".join(escape(c) for c in faltan)
        texto.append(f"<i>Sin precio ahora de: {nombres}. El total no las cuenta.</i>")

    return "\n".join(texto)


def formatear_compra(
    cantidad: float, coste: float, ahora: Posicion, currency: str
) -> str:
    """Lo que se contesta a un /compra: lo apuntado y como queda."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(ahora.coin_id.replace("-", " ").title())
    texto = (
        f"🛒 Apunto <b>{texto_cantidad(cantidad)}</b> de {nombre} "
        f"por {simbolo}{_num(coste)}.\n"
        f"Ahora tienes {texto_cantidad(ahora.cantidad)}"
    )
    if ahora.invertido is not None:
        texto += f", que te costaron {simbolo}{_num(ahora.invertido)}"
    return texto + ". Mira /cartera"


def formatear_venta(
    coin_id: str, vendido: float, queda: Posicion | None, currency: str
) -> str:
    """Lo que se contesta a un /venta. queda es None si ya no tienes nada."""
    nombre = escape(coin_id.replace("-", " ").title())
    texto = f"💸 Apunto la venta de <b>{texto_cantidad(vendido)}</b> de {nombre}.\n"
    if queda is None:
        return texto + f"Ya no te queda nada de {nombre}."

    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto += f"Te quedan {texto_cantidad(queda.cantidad)}"
    if queda.invertido is not None:
        texto += f", que te costaron {simbolo}{_num(queda.invertido)}"
    return texto + ". Mira /cartera"


def formatear_semana(
    semana: Semana, currency: str, desde: datetime | None = None
) -> str:
    """El resumen de los domingos. desde va solo si falta el principio."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["📅 <b>Tu semana</b>", ""]

    linea = f"Tu cartera vale <b>{simbolo}{_num(semana.fin)}</b>"
    if semana.porcentaje is not None:
        signo = "+" if semana.ganancia >= 0 else "-"
        linea += (
            f"\n{_flecha(semana.porcentaje)} {semana.porcentaje:+.2f}% "
            f"({signo}{simbolo}{_num(abs(semana.ganancia))}) en la semana"
        )
    texto.append(linea)

    if desde is not None:
        cuando = desde.astimezone()
        texto.append(f"<i>Solo tengo precios desde el {cuando:%d/%m a las %H:%M}.</i>")

    if semana.cambios:
        texto.append("")
        for coin_id, cambio in semana.cambios:
            nombre = escape(coin_id.replace("-", " ").title())
            texto.append(f"<b>{nombre}</b>  {_flecha(cambio)} {cambio:+.2f}%")

    return "\n".join(texto)


def formatear_busqueda(texto: str, resultados: list[dict]) -> str:
    """Respuesta de /buscar: los ids candidatos, el mas probable primero."""
    if not resultados:
        return f"No encuentro nada con <b>{escape(texto)}</b> en CoinGecko."

    lineas = [f"🔎 <b>{escape(texto)}</b>"]
    for m in resultados:
        rango = f" #{m['market_cap_rank']}" if m.get("market_cap_rank") else ""
        lineas.append(
            f"<code>{escape(m['id'])}</code> — {escape(m.get('name', ''))} "
            f"({escape(str(m.get('symbol', '')).upper())}){rango}"
        )

    lineas.append(
        f"\nEn WATCHLIST va el id, por ejemplo: "
        f"<code>{escape(resultados[0]['id'])}:%5</code>"
    )
    return "\n".join(lineas)


def formatear_puntual(alerta: Puntual, precio: float, currency: str) -> str:
    """Respuesta al crear una /alerta."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(alerta.coin_id.replace("-", " ").title())
    verbo = "suba" if alerta.sube else "baje"
    return (
        f"🎯 Te aviso cuando <b>{nombre}</b> {verbo} a "
        f"<b>{simbolo}{_num(alerta.objetivo)}</b>.\n"
        f"Ahora está a {simbolo}{_num(precio)}. Solo te aviso una vez."
    )


def formatear_puntuales(alertas: list[Puntual], currency: str) -> str:
    """Respuesta de /alertas."""
    if not alertas:
        return "No tienes alertas puestas. Crea una con /alerta bitcoin 70000"

    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    lineas = ["🎯 <b>Tus alertas</b>", ""]
    for a in alertas:
        nombre = escape(a.coin_id.replace("-", " ").title())
        flecha = "🔺" if a.sube else "🔻"
        lineas.append(
            f"<code>{a.id}</code>  <b>{nombre}</b> {flecha} {simbolo}{_num(a.objetivo)}"
        )
    lineas.append(f"\nPara quitar una: /quitar {alertas[0].id}")
    return "\n".join(lineas)


def describir(watch: Watch, currency: str) -> str:
    """Como se vigila una cripto, en cristiano: 'cada 5 % que se mueva'."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    if watch.percent is not None:
        return f"cada {watch.percent:g} % que se mueva".replace(".", ",")
    if watch.step is not None:
        return f"cada {simbolo}{_num(watch.step)}"

    lados = []
    if watch.min_price is not None:
        lados.append(f"si baja de {simbolo}{_num(watch.min_price)}")
    if watch.max_price is not None:
        lados.append(f"si sube de {simbolo}{_num(watch.max_price)}")
    return " o ".join(lados)


def formatear_vigiladas(
    watchlist: list[Watch], currency: str, desde_telegram: set[str]
) -> str:
    """Respuesta de /vigilar a secas."""
    lineas = ["👀 <b>Lo que vigilo</b>", ""]
    for w in watchlist:
        nombre = escape(w.coin_id.replace("-", " ").title())
        linea = f"<b>{nombre}</b>  {describir(w, currency)}"
        # Si no, no hay forma de saber por que no cuadra con el .env
        if w.coin_id in desde_telegram:
            linea += "  <i>(desde Telegram)</i>"
        lineas.append(linea)

    lineas.append("\nPara cambiarlo: /vigilar solana %5 o /dejar solana")
    return "\n".join(lineas)


def muestrear(precios: list[float], n: int) -> list[float]:
    """Se queda con n puntos repartidos, siempre con el primero y el ultimo."""
    if len(precios) <= n:
        return list(precios)

    paso = (len(precios) - 1) / (n - 1)
    return [precios[round(i * paso)] for i in range(n)]


def _siguiente(
    precio: float, arriba: float | None, abajo: float | None, simbolo: str
) -> str:
    """'↑ €64.000,00 (+1.59%) · ↓ €63.000,00 (-0.90%)'. Vacio si no hay nada."""
    # Entre ciclo y ciclo puede haberlo pasado ya; un "-52%" ahi no se entiende.
    if (arriba is not None and precio >= arriba) or (
        abajo is not None and precio < abajo
    ):
        return "Ya ha pasado su aviso, te llega en el próximo ciclo"

    lados = []
    for flecha, objetivo in (("↑", arriba), ("↓", abajo)):
        if objetivo is None or not precio:
            continue
        falta = (objetivo - precio) / precio * 100
        lados.append(f"{flecha} {simbolo}{_num(objetivo)} ({falta:+.2f}%)")
    return " · ".join(lados)


def _minutos(minutos: int) -> str:
    return f"{minutos // 60} h" if minutos % 60 == 0 else f"{minutos} min"


def _flecha(variacion: float) -> str:
    return "🔺" if variacion > 0 else "🔻" if variacion < 0 else "➖"


def _num(valor: float) -> str:
    """Formatea el numero segun su tamaño: 55.500 pero 0,3421."""
    if valor >= 1:
        texto = f"{valor:,.2f}"
    else:
        # Las criptos baratas necesitan mas decimales para verse.
        texto = f"{valor:,.4f}"

    # De formato ingles (1,234.56) a español (1.234,56).
    return texto.replace(",", "@").replace(".", ",").replace("@", ".")
