"""Compara precios con los umbrales y decide si hay que avisar."""

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime

from .caida import Caida
from .cartera import Valor, peso
from .comparar import Resultado
from .config import Posicion, Watch
from .correlacion import Correlacion
from .cuando import Cuando
from .dia import Dia
from .diasemana import DiasSemana
from .equilibrio import Cartera
from .horas import Horas
from .hoy import Hoy
from .maximo import Maximo, hace
from .mejor import Extremo
from .mercado import Mercado, grande
from .miedo import Indice
from .miedo import hace as dia_miedo
from .miedo import nombre as nombre_miedo
from .movimientos import Movimiento, texto_cantidad
from .objetivo import Escenario
from .periodo import nombre as nombre_periodo
from .puntuales import CARTERA, Puntual, cumplidas, ejemplo
from .racha import Racha
from .rango import Rango, barra
from .ratio import Ratio
from .reparto import Trozo
from .rsi import PERIODO, SOBRECOMPRA, SOBREVENTA, Rsi
from .semanal import Semana
from .sube import Subida
from .telegram import escape
from .tendencias import Tendencia
from .top import ENTRE, Movida
from .verdes import Verdes

logger = logging.getLogger(__name__)

# Estados en los que puede estar una cripto respecto a sus umbrales.
BAJO = "bajo"  # por debajo del minimo
NORMAL = "normal"  # entre los dos umbrales
ALTO = "alto"  # por encima del maximo

SIMBOLOS = {"eur": "€", "usd": "$", "gbp": "£"}

# Satoshis en un bitcoin, para /convertir.
POR_BTC = 100_000_000

# El plan gratis de CoinGecko pide citarles, con enlace, junto a los datos.
# La frase tiene que ser una de las suyas, por eso va en ingles.
FUENTE = '<i>Price data by <a href="https://www.coingecko.com">CoinGecko</a></i>'

# De menos a mas alto, para dibujar el historico en una linea.
BARRAS = "▁▂▃▄▅▆▇█"

# Mas barritas que esto y en el movil la linea salta a la siguiente.
BARRAS_MOVIL = 24
MINIMO_BARRAS = 6

# Ni la cripto mas barata necesita mas para que se vea su precio.
MAX_DECIMALES = 12


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
    extremo_dias: int | None = None  # solo en los de maximo o minimo de N dias
    nota: str | None = None  # la que escribiste en la /alerta


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

    if alerta.extremo_dias is not None:
        if alerta.estado == BAJO:
            icono, cual = "🕳", "mínimo"
        else:
            icono, cual = "🏔", "máximo"
        texto = (
            f"{icono} <b>{nombre}</b> marca su {cual} de {alerta.extremo_dias} días\n"
            f"Ahora a <b>{simbolo}{_num(alerta.price)}</b>, "
            f"el anterior era {simbolo}{_num(alerta.threshold)}"
        )
    elif alerta.minutos is not None:
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
    elif alerta.coin_id == CARTERA:
        texto = (
            f"{icono} <b>Tu cartera</b> {verbo} de {simbolo}{_num(alerta.threshold)}\n"
            f"Ahora vale <b>{simbolo}{_num(alerta.price)}</b>"
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
    if alerta.nota:
        texto += f"\n📝 {escape(alerta.nota)}"
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


def formatear_hoy(
    lineas: list[tuple[str, Hoy | None]], currency: str, ultimo: datetime
) -> str:
    """Respuesta de /hoy. ultimo es la hora del precio más nuevo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["☀️ <b>Hoy</b>, desde las 00:00", ""]
    for coin_id, h in lineas:
        nombre = escape(coin_id.replace("-", " ").title())
        if h is None:
            texto.append(f"<b>{nombre}</b>  <i>(sin precios de hoy)</i>")
            continue
        linea = f"<b>{nombre}</b>  {simbolo}{_num(h.ahora)}  "
        linea += f"{_flecha(h.cambio)} {h.cambio:+.2f}%"
        if h.desde is not None:
            linea += f" <i>(desde las {h.desde.astimezone():%H:%M})</i>"
        texto.append(linea)
        texto.append(
            f"   <i>máx {simbolo}{_num(h.maximo)} · mín {simbolo}{_num(h.minimo)}</i>"
        )
    texto.append(
        f"\n<i>Con lo guardado, lo último de las {ultimo.astimezone():%H:%M}</i>"
    )
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
            linea += (
                f"  {_flecha(v.porcentaje)} {v.porcentaje:+.2f}% "
                f"({_ganancia(v.ganancia, simbolo)})"
            )
        texto.append(linea)

        detalle = []
        # Con una sola, un "100% del total" no dice nada.
        parte = peso(v, total)
        if len(valores) > 1 and parte is not None:
            detalle.append(f"{_peso(parte)} del total")
        # Comparar los dos precios dice mas que el % para decidir si vender.
        if v.precio_medio is not None:
            detalle.append(
                f"te salió a {simbolo}{_num(v.precio_medio)} · "
                f"ahora {simbolo}{_num(v.precio)}"
            )
        if detalle:
            frase = " · ".join(detalle)
            texto.append(f"   <i>{frase[0].upper()}{frase[1:]}</i>")

    linea = f"\nTotal <b>{simbolo}{_num(total.valor)}</b>"
    if total.porcentaje is not None:
        linea += (
            f"  {_flecha(total.porcentaje)} {total.porcentaje:+.2f}% "
            f"({_ganancia(total.ganancia, simbolo)})"
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


def formatear_movimientos(
    lista: list[Movimiento], currency: str, coin_id: str | None = None
) -> str:
    """Respuesta de /movimientos: los ultimos, el mas reciente arriba."""
    de = f" de {escape(coin_id.replace('-', ' ').title())}" if coin_id else ""
    if not lista:
        return (
            f"No has apuntado ninguna compra ni venta{de} por aquí. "
            "Lo del PORTFOLIO del .env no sale."
        )
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    lineas = [f"📒 <b>Tus últimas compras y ventas{de}</b>"]
    for m in lista:
        nombre = escape(m.coin_id.replace("-", " ").title())
        cuando = m.cuando.astimezone()
        if m.tipo == "compra":
            linea = f"🛒 Compra de {texto_cantidad(m.cantidad)} de {nombre}"
            if m.coste is not None:
                linea += f" por {simbolo}{_num(m.coste)}"
        else:
            linea = f"💸 Venta de {texto_cantidad(m.cantidad)} de {nombre}"
        lineas.append(f"{linea}  <i>{cuando:%d/%m %H:%M}</i>")
    return "\n".join(lineas)


def formatear_deshecho(m: Movimiento, currency: str) -> str:
    """Lo que se contesta a un /deshacer: lo quitado y como vuelve a quedar."""
    nombre = escape(m.coin_id.replace("-", " ").title())
    texto = f"↩️ Quito la {m.tipo} de <b>{texto_cantidad(m.cantidad)}</b> de {nombre}.\n"
    if m.antes is None:
        return texto + f"No te queda nada de {nombre}."

    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto += f"Vuelves a tener {texto_cantidad(m.antes.cantidad)}"
    if m.antes.invertido is not None:
        texto += f", que te costaron {simbolo}{_num(m.antes.invertido)}"
    return texto + ". Mira /cartera"


def formatear_conversion(
    dinero: float,
    cripto: float,
    coin_id: str,
    precio: float,
    desde_dinero: bool,
    currency: str,
    sats: bool = False,
) -> str:
    """Respuesta de /convertir. Lo que escribiste va primero."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    lado_dinero = f"{simbolo}{_num(dinero)}"
    lado_cripto = _cripto(cripto, nombre, sats)
    if desde_dinero:
        linea = f"{lado_dinero} = <b>{lado_cripto}</b>"
    else:
        linea = f"{lado_cripto} = <b>{lado_dinero}</b>"
    texto = f"💱 {linea}\n<i>1 {nombre} = {simbolo}{_num(precio)}"
    if sats:
        texto += f" · 1 sat = {simbolo}{_num(precio / POR_BTC)}"
        texto += f"\n{_cripto(cripto, nombre, False)}"
    return texto + "</i>"


def _cripto(cantidad: float, nombre: str, sats: bool) -> str:
    """'0,05 Bitcoin', o '5.000.000 sats' si va en satoshis."""
    if sats:
        return f"{texto_cantidad(round(cantidad * POR_BTC))} sats"
    return f"{texto_cantidad(cantidad)} {nombre}"


def formatear_cambio(
    cantidad: float,
    coin_id: str,
    resultado: float,
    hacia: str,
    precios: tuple[float, float],
    currency: str,
    sats: bool = False,
    hacia_sats: bool = False,
) -> str:
    """Respuesta de /convertir de una cripto a otra."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    otra = escape(hacia.replace("-", " ").title())
    # Al revés también, que "1 BTC son 32 ETH" se entiende mejor que 0,03.
    return (
        f"💱 {_cripto(cantidad, nombre, sats)} = "
        f"<b>{_cripto(resultado, otra, hacia_sats)}</b>\n"
        f"<i>1 {otra} = {texto_cantidad(precios[1] / precios[0])} {nombre}\n"
        f"1 {nombre} = {simbolo}{_num(precios[0])} · "
        f"1 {otra} = {simbolo}{_num(precios[1])}</i>"
    )


def formatear_media(
    coin_id: str, ahora: float, medias: dict[int, float | None], currency: str
) -> str:
    """Respuesta de /media. medias va de los días de la ventana a su media."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    lineas = [f"📐 <b>{nombre}</b>  ahora {simbolo}{_num(ahora)}", ""]
    for dias, media in medias.items():
        if media is None:
            lineas.append(
                f"Media de {dias} días  <i>no tengo tantos días guardados</i>"
            )
            continue
        diferencia = (ahora / media - 1) * 100
        lado = "por encima" if diferencia >= 0 else "por debajo"
        lineas.append(
            f"Media de {dias} días  {simbolo}{_num(media)}  "
            f"{_flecha(diferencia)} {diferencia:+.2f}% {lado}"
        )
    lineas.append("\n<i>Con el precio del final de cada día</i>")
    return "\n".join(lineas)


def formatear_racha(coin_id: str, r: Racha, currency: str) -> str:
    """Respuesta de /racha."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    hacia = "subiendo" if r.sube else "bajando"
    dias = "1 día" if r.dias == 1 else f"{r.dias} días"
    # Si los datos se acaban antes que la racha, puede ser más larga.
    cuantos = dias if r.entera else f"al menos {dias}"
    return (
        f"{_flecha(r.cambio)} <b>{nombre}</b> lleva <b>{cuantos}</b> "
        f"{'' if r.dias == 1 else 'seguidos '}{hacia}, contando hoy\n"
        f"{r.cambio:+.2f}% desde el {r.desde:%d/%m}: "
        f"{simbolo}{_num(r.antes)} → {simbolo}{_num(r.ahora)}\n"
        "<i>Con el precio del final de cada día</i>"
    )


def formatear_rsi(coin_id: str, r: Rsi, currency: str) -> str:
    """Respuesta de /rsi."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    if r.valor >= SOBRECOMPRA:
        zona = "🔥 <b>Sobrecomprada</b>: ha subido mucho y rápido, suele frenar"
    elif r.valor <= SOBREVENTA:
        zona = "🧊 <b>Sobrevendida</b>: ha bajado mucho y rápido, suele rebotar"
    else:
        zona = "😐 <b>Neutral</b>: ni pasada de subidas ni de bajadas"

    texto = (
        f"📊 <b>{nombre}</b>, RSI de {PERIODO} días: <b>{r.valor:.0f}</b>\n"
        f"<code>0 {barra(r.valor)} 100</code>\n"
        f"{zona}\n\n"
        f"Ahora {simbolo}{_num(r.ahora)}\n"
        f"<i>Por encima de {SOBRECOMPRA} se dice sobrecomprada; por debajo de "
        f"{SOBREVENTA}, sobrevendida. Con el precio del final de cada día</i>"
    )
    # El suavizado tarda en asentarse: con pocos días no cuadra con las webs.
    if r.dias < 30:
        texto += (
            f"\n<i>Con solo {r.dias} días puede salir algo distinto que en otras "
            "webs.</i>"
        )
    return texto


def formatear_cuando(
    coin_id: str, c: Cuando, currency: str, ahora: datetime | None = None
) -> str:
    """Respuesta de /cuando."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    objetivo = f"{simbolo}{_num(c.objetivo)}"

    if c.objetivo == c.ahora:
        return f"🔎 <b>{nombre}</b> está justo a ese precio ahora, {objetivo}"
    if c.cuando is None:
        return (
            f"🔎 <b>{nombre}</b> no ha {'bajado' if c.por_debajo else 'subido'} "
            f"a {objetivo} desde el {c.desde.astimezone():%d/%m}, que es desde cuando "
            f"tengo precios\n"
            f"Lo más {'bajo' if c.por_debajo else 'alto'}, {simbolo}{_num(c.extremo)}. "
            f"Ahora {simbolo}{_num(c.ahora)}"
        )

    momento = c.cuando.astimezone()
    cuanto = hace(c.cuando, ahora or datetime.now(momento.tzinfo))
    # Si fue hoy, la hora dice más que la fecha.
    fecha = f"hoy a las {momento:%H:%M}" if cuanto == "hoy" else f"el {momento:%d/%m}"
    texto = (
        f"🔎 La última vez que <b>{nombre}</b> estuvo a <b>{objetivo}</b> o "
        f"{'menos' if c.por_debajo else 'más'} fue <b>{fecha}</b>"
    )
    if cuanto != "hoy":
        texto += f", {cuanto}"
    return (
        texto + f"\nEntonces {simbolo}{_num(c.precio)}, ahora {simbolo}{_num(c.ahora)} "
        f"({c.cambio:+.2f}%)"
    )


def formatear_dia(coin_id: str, d: Dia, currency: str, hoy: date | None = None) -> str:
    """Respuesta de /dia."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    hoy = hoy or date.today()
    if d.fecha == hoy:
        cuando, precio = "hoy", "Va por"
    else:
        formato = "%d/%m" if d.fecha.year == hoy.year else "%d/%m/%Y"
        cuando, precio = f"el {d.fecha:{formato}}", "Cerró a"

    texto = f"📅 <b>{nombre}</b> {cuando}\n\n{precio} <b>{simbolo}{_num(d.cierre)}</b>"
    # Con un solo precio guardado ese día, ni cambio ni máximo que contar.
    if d.maximo != d.minimo:
        texto += (
            f", {d.en_el_dia:+.2f}% en el día\n"
            f"<i>Máximo {simbolo}{_num(d.maximo)} · "
            f"mínimo {simbolo}{_num(d.minimo)}</i>"
        )
    if d.fecha != hoy:
        texto += (
            f"\n\n{_flecha(d.desde)} Desde entonces {d.desde:+.2f}%: "
            f"ahora {simbolo}{_num(d.ahora)}"
        )
    return texto


def formatear_copia(lineas: list[str]) -> str:
    """Respuesta de /copia."""
    return (
        "📋 <b>Cómo está ahora, para pegar en el .env</b>\n\n"
        f"<code>{escape(chr(10).join(lineas))}</code>\n\n"
        "<i>Ya incluye lo que has cambiado por Telegram. Guárdalo por si cambias de "
        "servidor o se pierde la base de datos.</i>"
    )


def formatear_correlacion(una: str, otra: str, c: Correlacion, horas: float) -> str:
    """Respuesta de /correlacion."""
    nombres = [escape(x.replace("-", " ").title()) for x in (una, otra)]
    if c.valor >= 0.7:
        como = "van muy juntas"
    elif c.valor >= 0.4:
        como = "suelen ir juntas"
    elif c.valor > -0.4:
        como = "cada una va a lo suyo"
    else:
        como = "suelen ir al revés"
    valor = f"{c.valor:+.2f}".replace(".", ",")
    return (
        f"🔗 <b>{nombres[0]}</b> y <b>{nombres[1]}</b>, {nombre_periodo(horas)}\n\n"
        f"Correlación <b>{valor}</b>: {como}\n"
        f"<code>-1 {barra((c.valor + 1) * 50)} +1</code>\n\n"
        f"<i>Con {c.dias} días. +1 es que se mueven igual, 0 que no tienen nada que "
        "ver y -1 que una sube cuando la otra baja</i>"
    )


def formatear_ratio(una: str, otra: str, r: Ratio, horas: float) -> str:
    """Respuesta de /ratio."""
    n1, n2 = (escape(x.replace("-", " ").title()) for x in (una, otra))
    valores = [v for _, v in r.dias]
    texto = (
        f"⚖️ <b>{n1}</b> en <b>{n2}</b>, {nombre_periodo(horas)}\n\n"
        f"1 {n1} = <b>{_num(r.ahora)}</b> {n2}\n"
        f"{_flecha(r.cambio)} {r.cambio:+.2f}% desde el {r.desde:%d/%m} "
        f"({_num(r.antes)})\n"
    )
    if len(valores) >= MINIMO_BARRAS:
        texto += f"<code>{sparkline(muestrear(valores, BARRAS_MOVIL))}</code>\n"
    texto += (
        f"Máximo {_num(max(valores))} · Mínimo {_num(min(valores))}\n\n"
        f"<i>Si sube, a {n1} le ha ido mejor que a {n2}. "
        "Con el precio del final de cada día</i>"
    )
    return texto


def formatear_reparto(trozos: list[Trozo], total: float, currency: str) -> str:
    """Respuesta de /reparto, y el pie de su imagen."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    lineas = [f"🥧 <b>Tu cartera</b>: {simbolo}{_num(total)}", ""]
    for t in trozos:
        nombre = escape(t.coin_id.replace("-", " ").title())
        lineas.append(f"<b>{nombre}</b> {t.peso:.0f}% · {simbolo}{_num(t.valor)}")
    return "\n".join(lineas)


def formatear_rango(
    coin_id: str, r: Rango, horas: float, currency: str, desde: datetime | None = None
) -> str:
    """Respuesta de /rango. desde va si no hay precios de todo el tramo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    del_maximo = (r.ahora / r.maximo - 1) * 100
    del_minimo = (r.ahora / r.minimo - 1) * 100

    texto = (
        f"📏 <b>{nombre}</b>, {nombre_periodo(horas)}\n\n"
        f"Máximo {simbolo}{_num(r.maximo)}  <i>el {r.cuando_maximo.astimezone():%d/%m}"
        f" · ahora {del_maximo:+.2f}%</i>\n"
        f"Mínimo {simbolo}{_num(r.minimo)}  <i>el {r.cuando_minimo.astimezone():%d/%m}"
        f" · ahora {del_minimo:+.2f}%</i>\n"
        f"Media {simbolo}{_num(r.media)}\n\n"
        f"Ahora <b>{simbolo}{_num(r.ahora)}</b>"
    )
    if r.posicion is None:
        texto += "\n<i>No se ha movido nada en este tramo</i>"
    else:
        texto += (
            f", al {r.posicion:.0f}% del rango\n"
            f"<code>mín {barra(r.posicion)} máx</code>"
        )
    if desde is not None:
        cuando = desde.astimezone()
        texto += f"\n<i>Solo tengo precios desde el {cuando:%d/%m a las %H:%M}.</i>"
    return texto


def formatear_caida(
    coin_id: str, c: Caida, horas: float, currency: str, desde: datetime | None = None
) -> str:
    """Respuesta de /caida. desde va si no hay precios de todo el tramo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())

    texto = f"📉 <b>{nombre}</b>, {nombre_periodo(horas)}\n\n"
    if c.desde_maximo == 0:
        texto += f"Ahora <b>{simbolo}{_num(c.ahora)}</b>, está en su máximo del tramo\n"
    else:
        texto += (
            f"Ahora <b>{simbolo}{_num(c.ahora)}</b>, "
            f"<b>{c.desde_maximo:+.2f}%</b> desde el máximo\n"
            f"<i>Máximo {simbolo}{_num(c.maximo)} el "
            f"{c.cuando_maximo.astimezone():%d/%m}</i>\n"
        )
    if c.peor == 0:
        texto += "\nNo ha tenido ninguna caída en este tramo"
    else:
        texto += (
            f"\nPeor caída <b>{c.peor:+.2f}%</b>: de {simbolo}{_num(c.pico)} el "
            f"{c.cuando_pico.astimezone():%d/%m} a {simbolo}{_num(c.valle)} el "
            f"{c.cuando_valle.astimezone():%d/%m}"
        )
    if desde is not None:
        cuando = desde.astimezone()
        texto += f"\n<i>Solo tengo precios desde el {cuando:%d/%m a las %H:%M}.</i>"
    return texto


def formatear_sube(
    coin_id: str, s: Subida, horas: float, currency: str, desde: datetime | None = None
) -> str:
    """Respuesta de /sube. desde va si no hay precios de todo el tramo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())

    texto = f"🚀 <b>{nombre}</b>, {nombre_periodo(horas)}\n\n"
    if s.desde_minimo == 0:
        texto += f"Ahora <b>{simbolo}{_num(s.ahora)}</b>, está en su mínimo del tramo\n"
    else:
        texto += (
            f"Ahora <b>{simbolo}{_num(s.ahora)}</b>, "
            f"<b>{s.desde_minimo:+.2f}%</b> desde el mínimo\n"
            f"<i>Mínimo {simbolo}{_num(s.minimo)} el "
            f"{s.cuando_minimo.astimezone():%d/%m}</i>\n"
        )
    if s.mejor == 0:
        texto += "\nNo ha tenido ninguna subida en este tramo"
    else:
        texto += (
            f"\nMejor subida <b>{s.mejor:+.2f}%</b>: de {simbolo}{_num(s.valle)} el "
            f"{s.cuando_valle.astimezone():%d/%m} a {simbolo}{_num(s.pico)} el "
            f"{s.cuando_pico.astimezone():%d/%m}"
        )
    if desde is not None:
        cuando = desde.astimezone()
        texto += f"\n<i>Solo tengo precios desde el {cuando:%d/%m a las %H:%M}.</i>"
    return texto


def formatear_extremo(
    coin_id: str, e: Extremo, horas: float, currency: str, desde: date | None = None
) -> str:
    """Respuesta de /extremo. desde va si no hay precios de todo el tramo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    texto = f"🎢 <b>{nombre}</b>, {nombre_periodo(horas)}\n"

    # Si todos los días bajaron, el "mejor" sería una bajada: queda raro.
    for titulo, d, vale, nada in (
        ("Mejor día", e.mejor, e.mejor.cambio > 0, "No ha subido ningún día"),
        ("Peor día", e.peor, e.peor.cambio < 0, "No ha bajado ningún día"),
    ):
        if vale:
            texto += (
                f"\n{_flecha(d.cambio)} {titulo}: <b>{d.cambio:+.2f}%</b> "
                f"el {d.dia:%d/%m}\n"
                f"<i>{simbolo}{_num(d.antes)} → {simbolo}{_num(d.precio)}</i>\n"
            )
        else:
            texto += f"\n{nada}\n"

    texto += "\n<i>Con el precio del final de cada día</i>"
    if desde is not None:
        texto += f"\n<i>Solo tengo precios desde el {desde:%d/%m}.</i>"
    return texto


def formatear_verdes(
    coin_id: str, v: Verdes, horas: float, incompleto: bool = False
) -> str:
    """Respuesta de /verdes. incompleto si no hay precios de todo el tramo."""
    nombre = escape(coin_id.replace("-", " ").title())
    pct = v.porcentaje
    icono = "🟢" if pct > 50 else "🔴" if pct < 50 else "⚪"
    verdes = round(pct / 10)

    texto = (
        f"{icono} <b>{nombre}</b>, {nombre_periodo(horas)}\n\n"
        f"<b>{v.suben}</b> en verde y <b>{v.bajan}</b> en rojo"
    )
    if v.iguales:
        texto += f" ({v.iguales} sin cambios)"
    texto += (
        f"\n{'🟩' * verdes}{'🟥' * (10 - verdes)} sube el <b>{pct:.0f}%</b> "
        "de los días\n"
        "<i>Con el precio del final de cada día</i>"
    )
    if incompleto:
        texto += f"\n<i>Solo tengo precios desde el {v.desde:%d/%m}.</i>"
    return texto


def formatear_diasemana(
    coin_id: str, s: DiasSemana, horas: float, incompleto: bool = False
) -> str:
    """Respuesta de /diasemana. incompleto si no hay precios de todo el tramo."""
    nombre = escape(coin_id.replace("-", " ").title())
    texto = f"📅 <b>{nombre}</b> por días de la semana, {nombre_periodo(horas)}\n\n"
    for d in s.dias:
        texto += f"{_flecha(d.media)} {d.nombre}: <b>{d.media:+.2f}%</b> · {d.veces}\n"

    # Con un solo día no hay nada que comparar.
    if len(s.dias) > 1:
        texto += (
            f"\nMejor: <b>{s.mejor.nombre.lower()}</b> · "
            f"Peor: <b>{s.peor.nombre.lower()}</b>\n"
        )
    texto += "<i>Lo que cambia de media ese día y cuántas veces lo he visto</i>"
    if incompleto:
        texto += f"\n<i>Solo tengo precios desde el {s.desde:%d/%m}.</i>"
    return texto


def formatear_horas(coin_id: str, h: Horas, horas: float) -> str:
    """Respuesta de /horas."""
    nombre = escape(coin_id.replace("-", " ").title())
    barata, cara = h.medias[h.barata], h.medias[h.cara]
    texto = (
        f"🕐 <b>{nombre}</b> por horas, {nombre_periodo(horas)}\n\n"
        f"🟢 Más barata sobre las <b>{h.barata:02d}:00</b> ({barata:+.2f}%)\n"
        f"🔴 Más cara sobre las <b>{h.cara:02d}:00</b> ({cara:+.2f}%)\n"
    )
    # Si falta alguna hora, las etiquetas de los lados mentirían.
    if len(h.medias) == 24:
        texto += f"\n<code>00h {sparkline(list(h.medias.values()))} 23h</code>\n"

    dias = "1 día completo" if h.dias == 1 else f"{h.dias} días completos"
    texto += f"\n<i>Comparado con la media de cada día, en {dias}</i>"
    if cara - barata < 0.5:
        texto += "\n<i>La diferencia es pequeña: no lo tomes como una regla.</i>"
    return texto


def formatear_equilibrio(c: Cartera, currency: str) -> str:
    """Respuesta de /equilibrio."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🧮 <b>Para no perder</b>", ""]
    for e in c.criptos:
        nombre = escape(e.coin_id.replace("-", " ").title())
        if e.falta > 0:
            como = f"falta <b>{e.falta:+.2f}%</b>"
        else:
            como = f"ya ganas, aguanta <b>{e.falta:+.2f}%</b>"
        texto.append(
            f"{'🔴' if e.falta > 0 else '🟢'} <b>{nombre}</b> a "
            f"{simbolo}{_num(e.medio)} · {como}"
        )
        texto.append(f"   <i>ahora {simbolo}{_num(e.precio)}</i>")

    if c.total is not None:
        if c.total > 0:
            texto.append(f"\n📦 Todo junto tendría que subir un <b>{c.total:+.2f}%</b>")
        else:
            texto.append(
                f"\n📦 Todo junto vas ganando: aguanta una bajada del "
                f"<b>{-c.total:.2f}%</b>"
            )
    if c.sin_coste:
        nombres = ", ".join(escape(x.replace("-", " ").title()) for x in c.sin_coste)
        texto.append(f"\n<i>De {nombres} no sé lo que te costó.</i>")
    return "\n".join(texto)


def formatear_objetivo(e: Escenario, currency: str) -> str:
    """Respuesta de /objetivo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(e.coin_id.replace("-", " ").title())
    diferencia = e.despues - e.ahora

    texto = (
        f"🎯 Si <b>{nombre}</b> llega a <b>{simbolo}{_num(e.objetivo)}</b> "
        f"({e.cambio:+.2f}%), tu cartera valdría <b>{simbolo}{_num(e.despues)}</b>\n"
        f"{_flecha(diferencia)} {_ganancia(diferencia, simbolo)} respecto a hoy "
        f"({simbolo}{_num(e.ahora)})"
    )
    if e.invertido:
        ganancia = e.despues - e.invertido
        texto += (
            f"\nSobre lo invertido, {_ganancia(ganancia, simbolo)} "
            f"({ganancia / e.invertido * 100:+.2f}%)"
        )
    return texto + (
        f"\n<i>Tus {texto_cantidad(e.cantidad)} {nombre} pasarían de "
        f"{simbolo}{_num(e.cantidad * e.precio)} a "
        f"{simbolo}{_num(e.cantidad * e.objetivo)}</i>"
    )


def formatear_hubiera(
    cantidad: float,
    coin_id: str,
    antes: float,
    ahora: float,
    horas: float,
    desde: datetime | None,
    currency: str,
    ultimo: datetime | None = None,
) -> str:
    """Respuesta de /si. desde va si no hay precios de todo el tramo pedido,
    y ultimo si el precio de "ahora" es viejo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    valor = cantidad * ahora / antes
    porcentaje = (ahora / antes - 1) * 100
    cuando = f"el {desde.astimezone():%d/%m}" if desde else _hace(horas)

    texto = (
        f"🔮 Si hubieras metido {simbolo}{_num(cantidad)} en <b>{nombre}</b> "
        f"{cuando}, hoy tendrías <b>{simbolo}{_num(valor)}</b>\n"
        f"{_flecha(porcentaje)} {porcentaje:+.2f}% "
        f"({_ganancia(valor - cantidad, simbolo)})\n"
        f"<i>Entonces {simbolo}{_num(antes)} · ahora {simbolo}{_num(ahora)}</i>"
    )
    if desde:
        texto += f"\n<i>Solo tengo precios desde entonces, no de {_hace(horas)}</i>"
    if ultimo:
        fecha = ultimo.astimezone()
        texto += f"\n<i>El último precio que tengo es del {fecha:%d/%m a las %H:%M}</i>"
    return texto


def formatear_dca(
    cantidad: float,
    coin_id: str,
    cada: str,
    compras: int,
    cripto: float,
    valor: float,
    horas: float,
    desde: datetime | None,
    currency: str,
    ultimo: datetime | None = None,
) -> str:
    """Respuesta de /dca. desde y ultimo, como en /si."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    invertido = cantidad * compras
    porcentaje = (valor / invertido - 1) * 100
    cuando = f"desde el {desde.astimezone():%d/%m}" if desde else _hace(horas)
    veces = "1 compra" if compras == 1 else f"{compras} compras"

    texto = (
        f"🔁 Metiendo {simbolo}{_num(cantidad)} en <b>{nombre}</b> {cada} "
        f"{cuando}, hoy tendrías <b>{simbolo}{_num(valor)}</b>\n"
        f"{_flecha(porcentaje)} {porcentaje:+.2f}% "
        f"({_ganancia(valor - invertido, simbolo)})\n"
        f"<i>{veces}, {simbolo}{_num(invertido)} en total · "
        f"precio medio {simbolo}{_num(invertido / cripto)}</i>"
    )
    if desde:
        texto += f"\n<i>Solo tengo precios desde entonces, no de {_hace(horas)}</i>"
    if ultimo:
        fecha = ultimo.astimezone()
        texto += f"\n<i>El último precio que tengo es del {fecha:%d/%m a las %H:%M}</i>"
    return texto


def _hace(horas: float) -> str:
    """'hace 30 días', 'hace 12 h'."""
    if horas >= 48 and horas % 24 == 0:
        return f"hace {int(horas // 24)} días"
    return f"hace {horas:g} h".replace(".", ",")


def formatear_precio(
    coin_id: str,
    precio: float,
    variacion: float | None,
    currency: str,
    en_7d: float | None = None,
    en_1h: float | None = None,
    tuyo: Valor | None = None,
    dia: list[float] | None = None,
) -> str:
    """Respuesta de /precio: lo que vale ahora y cómo va en 1 h, 24 h y 7 días.

    tuyo es lo que tienes de ella, si esta en la cartera. dia, los precios
    guardados de las últimas 24 h, para las barritas."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    texto = f"💰 <b>{nombre}</b>  {simbolo}{_num(precio)}"
    if en_1h is not None:
        texto += f"\n{_flecha(en_1h)} {en_1h:+.2f}% en 1 h"
    if variacion is None:
        texto += "\n<i>Sin datos de las últimas 24 h</i>"
    else:
        texto += f"\n{_flecha(variacion)} {variacion:+.2f}% en 24 h"
    if en_7d is not None:
        texto += f"\n{_flecha(en_7d)} {en_7d:+.2f}% en 7 días"
    # Con cuatro puntos las barritas no dicen nada.
    if dia and len(dia) >= MINIMO_BARRAS:
        texto += f"\n<code>{sparkline(muestrear(dia, BARRAS_MOVIL))}</code> <i>24 h</i>"
    if tuyo is not None:
        texto += (
            f"\n\n💼 Tienes {texto_cantidad(tuyo.cantidad)}, "
            f"que valen <b>{simbolo}{_num(tuyo.valor)}</b>"
        )
        if tuyo.porcentaje is not None:
            texto += (
                f"  {_flecha(tuyo.porcentaje)} {tuyo.porcentaje:+.2f}% "
                f"({_ganancia(tuyo.ganancia, simbolo)})"
            )
    return texto


def formatear_precios(
    lineas: list[tuple[str, float, float | None, float | None]],
    faltan: list[str],
    currency: str,
) -> str:
    """/precio de varias: (cripto, precio, en 24 h, en 7 dias), una por linea."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["💰 <b>Precio ahora</b> · <i>en 24 h y en 7 días</i>", ""]
    for coin_id, precio, variacion, en_7d in lineas:
        nombre = escape(coin_id.replace("-", " ").title())
        linea = f"<b>{nombre}</b>  {simbolo}{_num(precio)}"
        if variacion is not None:
            linea += f"  {_flecha(variacion)} {variacion:+.2f}%"
        if en_7d is not None:
            # Sin el de 24 h, el que queda podria pasar por el de hoy.
            linea += (
                f" · {en_7d:+.2f}% 7d" if variacion is None else f" · {en_7d:+.2f}%"
            )
        texto.append(linea)

    if faltan:
        texto += ["", formatear_no_encuentro(faltan)]
    return "\n".join(texto)


def formatear_maximo(m: Maximo, currency: str, ahora: datetime) -> str:
    """/ath de una: el maximo, cuando fue y cuanto le falta para volver."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(m.coin_id.replace("-", " ").title())
    texto = (
        f"🏔 <b>{nombre}</b>  máximo histórico {simbolo}{_num(m.maximo)}\n"
        f"<i>El {m.fecha.astimezone():%d/%m/%Y}, {hace(m.fecha, ahora)}</i>\n"
        f"Ahora {simbolo}{_num(m.precio)} · "
    )
    if not m.falta():
        return texto + "🎉 está en máximos"
    return texto + f"le falta +{m.falta():.2f}% para volver"


def formatear_maximos(maximos: list[Maximo], faltan: list[str], currency: str) -> str:
    """/ath de varias, una por linea."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🏔 <b>Máximo histórico</b> · <i>lo que le falta</i>", ""]
    for m in maximos:
        nombre = escape(m.coin_id.replace("-", " ").title())
        falta = f"+{m.falta():.2f}%" if m.falta() else "🎉 en máximos"
        texto.append(
            f"<b>{nombre}</b>  {simbolo}{_num(m.maximo)} "
            f"<i>({m.fecha.astimezone():%m/%Y})</i>  {falta}"
        )

    if faltan:
        texto += ["", formatear_no_encuentro(faltan)]
    return "\n".join(texto)


def formatear_tendencias(lista: list[Tendencia]) -> str:
    """/tendencias: una por linea, con su puesto y como va en 24 h."""
    if not lista:
        return "CoinGecko no me ha dado tendencias ahora mismo. Prueba en un rato."

    texto = ["🔥 <b>Lo que más se busca hoy</b> · <i>en 24 h</i>", ""]
    for n, t in enumerate(lista, 1):
        linea = f"{n}. <b>{escape(t.nombre)}</b>"
        if t.simbolo:
            linea += f" {escape(t.simbolo)}"
        if t.puesto:
            linea += f" <i>#{t.puesto}</i>"
        if t.variacion is not None:
            linea += f"  {_flecha(t.variacion)} {t.variacion:+.2f}%"
        texto.append(linea)

    texto += ["", "<i>Toca una para ver su precio y ponerle una alerta</i>"]
    return "\n".join(texto)


def formatear_top(suben: list[Movida], bajan: list[Movida], currency: str) -> str:
    """/top: las que mas suben y las que mas bajan, cada una con su precio."""
    if not suben and not bajan:
        return "CoinGecko no me ha dado los precios ahora mismo. Prueba en un rato."

    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [f"🏆 <b>Lo que más se mueve hoy</b> · <i>de las {ENTRE} más grandes</i>"]
    for titulo, lista, vacia in (
        ("🔺 <b>Suben</b>", suben, "Hoy no sube ninguna."),
        ("🔻 <b>Bajan</b>", bajan, "Hoy no baja ninguna."),
    ):
        texto += ["", titulo]
        if not lista:
            texto.append(f"<i>{vacia}</i>")
        for m in lista:
            nombre = escape(m.simbolo or m.nombre)
            texto.append(
                f"<b>{nombre}</b>  {m.variacion:+.2f}%  "
                f"<i>{simbolo}{_num(m.precio)}</i>"
            )
    return "\n".join(texto)


def formatear_miedo(lista: list[Indice]) -> str:
    """/miedo: el de hoy con una barra, y ayer y hace una semana para comparar."""
    if not lista:
        return "No me han dado el índice ahora mismo. Prueba en un rato."

    hoy = lista[0]
    emoji, nombre = nombre_miedo(hoy)
    llenas = round(hoy.valor / 10)
    texto = [
        f"{emoji} <b>Miedo y codicia: {hoy.valor}</b> · {escape(nombre)}",
        f"{'▰' * llenas}{'▱' * (10 - llenas)}",
    ]
    antes = []
    for dias, cuando in ((1, "Ayer"), (7, "Hace una semana")):
        i = dia_miedo(lista, dias)
        if i is not None:
            antes.append(f"{cuando} {i.valor} {nombre_miedo(i)[0]}")
    if antes:
        texto.append(" · ".join(antes))
    texto += [
        "",
        "<i>0 es pánico y 100 euforia. Datos de "
        '<a href="https://alternative.me/crypto/fear-and-greed-index/">'
        "alternative.me</a></i>",
    ]
    return "\n".join(texto)


def linea_miedo(lista: list[Indice]) -> str | None:
    """El indice en una linea, para el resumen del dia. None si no vino."""
    if not lista:
        return None
    hoy = lista[0]
    emoji, nombre = nombre_miedo(hoy)
    linea = f"{emoji} Miedo y codicia: <b>{hoy.valor}</b> · {escape(nombre)}"
    ayer = dia_miedo(lista, 1)
    if ayer is not None:
        linea += f"  <i>(ayer {ayer.valor})</i>"
    return linea


def formatear_mercado(m: Mercado, currency: str) -> str:
    """/mercado: el total, como va y cuanto es de Bitcoin, Ethereum y las estables."""
    if m.total is None and m.bitcoin is None:
        return "CoinGecko no me ha dado los datos del mercado. Prueba en un rato."

    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🌍 <b>Mercado cripto</b>"]
    if m.total is not None:
        texto[0] += f"  {simbolo}{grande(m.total)}"
    if m.variacion is not None:
        texto.append(f"{_flecha(m.variacion)} {m.variacion:+.2f}% en 24 h")

    partes = [
        (nombre, valor)
        for nombre, valor in (
            ("Bitcoin", m.bitcoin),
            ("Ethereum", m.ethereum),
            ("Estables", m.estables),
        )
        if valor is not None
    ]
    if partes:
        texto.append("")
        texto += [
            f"<b>{nombre}</b>  {valor:.1f}% del total" for nombre, valor in partes
        ]
    if m.estables is not None:
        texto.append("<i>Estables son USDT y USDC: dinero aparcado esperando</i>")
    return "\n".join(texto)


def formatear_comparar(
    resultados: list[Resultado], sin_datos: list[str], horas: float
) -> str:
    """/comparar: de mejor a peor, las tres primeras con medalla."""
    medallas = ["🥇", "🥈", "🥉"]
    texto = [f"📊 <b>Cómo les ha ido</b> · <i>{nombre_periodo(horas)}</i>", ""]
    for n, r in enumerate(resultados):
        puesto = medallas[n] if n < len(medallas) else f"{n + 1}."
        nombre = escape(r.coin_id.replace("-", " ").title())
        linea = (
            f"{puesto} <b>{nombre}</b>  {_flecha(r.porcentaje)} {r.porcentaje:+.2f}%"
        )
        if r.desde and r.hasta:
            linea += (
                f" <i>(del {r.desde.astimezone():%d/%m} "
                f"al {r.hasta.astimezone():%d/%m})</i>"
            )
        elif r.desde:
            linea += f" <i>(desde el {r.desde.astimezone():%d/%m})</i>"
        elif r.hasta:
            linea += f" <i>(hasta el {r.hasta.astimezone():%d/%m})</i>"
        texto.append(linea)

    if sin_datos:
        nombres = ", ".join(f"<b>{escape(c)}</b>" for c in sin_datos)
        texto += ["", f"<i>No tengo precios guardados de {nombres}.</i>"]
    return "\n".join(texto)


def formatear_volatilidad(
    coin_id: str,
    horas: float,
    media: float,
    peor: float,
    peor_dia: date,
    dias: int,
    avisos: dict[int, int],
    desde: datetime | None,
) -> str:
    """/volatilidad: lo que se mueve al dia y los avisos que habria dado cada %."""
    nombre = escape(coin_id.replace("-", " ").title())
    texto = [
        f"〰️ <b>{nombre}</b> · <i>{nombre_periodo(horas)}</i>",
        f"Se mueve de media un <b>{media:.2f}%</b> al día "
        f"<i>({'1 día' if dias == 1 else f'{dias} días'})</i>",
        f"El día que más: {_flecha(peor)} {peor:+.2f}% el {peor_dia:%d/%m}",
        "",
        f"Con /vigilar {escape(coin_id)} te habría avisado:",
    ]
    for porcentaje, veces in avisos.items():
        cuantas = {0: "ninguna", 1: "1 vez"}.get(veces, f"{veces} veces")
        texto.append(f"%{porcentaje} → {cuantas}")
    if desde:
        texto.append(f"\n<i>Solo tengo precios desde el {desde.astimezone():%d/%m}</i>")
    return "\n".join(texto)


def formatear_no_encuentro(coin_ids: list[str]) -> str:
    nombres = ", ".join(f"<b>{escape(c)}</b>" for c in coin_ids)
    return (
        f"No encuentro {nombres} en CoinGecko. Prueba con /buscar {escape(coin_ids[0])}"
    )


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

    # En <code> se copia de un toque; como enlace mandaria /vigilar a secas.
    lineas.append(
        f"\nPara vigilarla: <code>/vigilar {escape(resultados[0]['id'])} %5</code>"
    )
    return "\n".join(lineas)


def formatear_puntual(alerta: Puntual, precio: float, currency: str) -> str:
    """Respuesta al crear una /alerta."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    verbo = "suba" if alerta.sube else "baje"
    una_vez = "Solo te aviso una vez."
    if alerta.caduca:
        una_vez = (
            f"Solo te aviso una vez, y si no llega, se borra el "
            f"{alerta.caduca.astimezone():%d/%m a las %H:%M}."
        )
    if alerta.coin_id == CARTERA:
        texto = (
            f"🎯 Te aviso cuando <b>tu cartera</b> {verbo} a "
            f"<b>{simbolo}{_num(alerta.objetivo)}</b>.\n"
            f"Ahora vale {simbolo}{_num(precio)}. {una_vez}"
        )
    else:
        nombre = escape(alerta.coin_id.replace("-", " ").title())
        texto = (
            f"🎯 Te aviso cuando <b>{nombre}</b> {verbo} a "
            f"<b>{simbolo}{_num(alerta.objetivo)}</b>.\n"
            f"Ahora está a {simbolo}{_num(precio)}. {una_vez}"
        )
    if alerta.nota:
        texto += f"\n📝 {escape(alerta.nota)}"
    return texto


def formatear_sin_objetivo(coin_id: str, precio: float, currency: str) -> str:
    """/alerta con la cripto pero sin precio: a cuanto esta y un ejemplo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    if coin_id == CARTERA:
        ahora = f"💰 <b>Tu cartera</b> vale {simbolo}{_num(precio)}."
    else:
        nombre = escape(coin_id.replace("-", " ").title())
        ahora = f"💰 <b>{nombre}</b> está a {simbolo}{_num(precio)}."
    comando = f"/alerta {escape(coin_id)}"
    return (
        f"{ahora}\n¿A cuánto te aviso? Por ejemplo {comando} {ejemplo(precio)} "
        f"o {comando} +10%"
    )


def formatear_puntuales(
    alertas: list[Puntual], currency: str, precios: dict[str, float] | None = None
) -> str:
    """Respuesta de /alertas. Con precios, dice cuanto le falta a cada una."""
    if not alertas:
        return "No tienes alertas puestas. Crea una con /alerta bitcoin 70000"

    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    lineas = ["🎯 <b>Tus alertas</b>", ""]
    for a in alertas:
        nombre = (
            "Tu cartera"
            if a.coin_id == CARTERA
            else escape(a.coin_id.replace("-", " ").title())
        )
        flecha = "🔺" if a.sube else "🔻"
        linea = (
            f"<code>{a.id}</code>  <b>{nombre}</b> {flecha} {simbolo}{_num(a.objetivo)}"
        )
        if a.caduca:
            linea += f"  ⌛ {a.caduca.astimezone():%d/%m}"
        falta = _falta((precios or {}).get(a.coin_id), a)
        lineas.append(f"{linea}  <i>{falta}</i>" if falta else linea)
        if a.nota:
            lineas.append(f"      📝 {escape(a.nota)}")
    lineas.append(f"\nPara quitar una: /quitar {alertas[0].id}")
    if len(alertas) > 1:
        lineas[-1] += " · todas: /quitar todas"
    return "\n".join(lineas)


def formatear_cerca(cerca: list[tuple[Puntual, float]], currency: str) -> str:
    """Las /alerta que estan a punto, para el resumen del dia."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    lineas = ["🎯 <b>A punto de saltar</b>"]
    for a, falta in cerca:
        nombre = (
            "Tu cartera"
            if a.coin_id == CARTERA
            else escape(a.coin_id.replace("-", " ").title())
        )
        flecha = "🔺" if a.sube else "🔻"
        lineas.append(
            f"<b>{nombre}</b> {flecha} {simbolo}{_num(a.objetivo)}  "
            f"<i>(falta {falta:+.2f}%)</i>"
        )
        if a.nota:
            lineas.append(f"      📝 {escape(a.nota)}")
    return "\n".join(lineas)


def formatear_lejos(cuantas: int, a: Puntual, falta: float, currency: str) -> str:
    """Si ninguna esta a punto, una linea para que no se te olvide que las tienes."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = (
        "Tu cartera"
        if a.coin_id == CARTERA
        else escape(a.coin_id.replace("-", " ").title())
    )
    flecha = "🔺" if a.sube else "🔻"
    tienes = "Tienes 1 alerta" if cuantas == 1 else f"Tienes {cuantas} alertas"
    cual = "" if cuantas == 1 else ", la más cerca"
    return (
        f"🎯 {tienes}{cual}: <b>{nombre}</b> {flecha} {simbolo}{_num(a.objetivo)}  "
        f"<i>(falta {falta:+.2f}%)</i>"
    )


def formatear_caducadas(alertas: list[Puntual], currency: str) -> str:
    """Las de /alerta que se han borrado por tiempo sin llegar a su precio."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    titulo = "Ha caducado" if len(alertas) == 1 else "Han caducado"
    lineas = [f"⌛ <b>{titulo} sin llegar</b>", ""]
    for a in alertas:
        nombre = (
            "Tu cartera"
            if a.coin_id == CARTERA
            else escape(a.coin_id.replace("-", " ").title())
        )
        flecha = "🔺" if a.sube else "🔻"
        linea = f"<b>{nombre}</b> {flecha} {simbolo}{_num(a.objetivo)}"
        lineas.append(f"{linea}  📝 {escape(a.nota)}" if a.nota else linea)
    lineas.append("\n<i>Si te sigue interesando, vuelve a ponerla con /alerta</i>")
    return "\n".join(lineas)


def formatear_quitadas(quitadas: list[int], no_estaban: list[int]) -> str:
    """Respuesta de /quitar con los numeros que habia y los que no."""
    lineas = []
    if len(quitadas) == 1:
        lineas.append("🗑 Alerta quitada.")
    elif quitadas:
        lineas.append(f"🗑 {len(quitadas)} alertas quitadas.")

    if len(no_estaban) == 1:
        lineas.append(
            f"No tengo ninguna alerta con el número {no_estaban[0]}. Mira /alertas"
        )
    elif no_estaban:
        numeros = ", ".join(str(n) for n in no_estaban[:-1])
        lineas.append(
            f"No tengo ninguna alerta con los números {numeros} y {no_estaban[-1]}. "
            "Mira /alertas"
        )
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


def _falta(precio: float | None, alerta: Puntual) -> str:
    """'(falta +3.20%)'. Vacio si no hay precio con el que comparar."""
    if not precio:
        return ""
    # Entre ciclo y ciclo puede haber llegado ya; saltara en el siguiente.
    if cumplidas([alerta], {alerta.coin_id: precio}):
        return "(ya ha llegado, te aviso en el próximo ciclo)"
    return f"(falta {(alerta.objetivo - precio) / precio * 100:+.2f}%)"


def _ganancia(ganancia: float, simbolo: str) -> str:
    """'+€20,00' o '-€200,00'."""
    signo = "+" if ganancia >= 0 else "-"
    return f"{signo}{simbolo}{_num(abs(ganancia))}"


def _peso(porcentaje: float) -> str:
    # Un "0%" parece que no tienes nada; va escapado, que el mensaje es HTML.
    return f"{porcentaje:.0f}%" if porcentaje >= 1 else "&lt;1%"


def _minutos(minutos: int) -> str:
    return f"{minutos // 60} h" if minutos % 60 == 0 else f"{minutos} min"


def _flecha(variacion: float) -> str:
    return "🔺" if variacion > 0 else "🔻" if variacion < 0 else "➖"


def _num(valor: float) -> str:
    """Formatea el numero segun su tamaño: 55.500, 0,3421 o 0,00001234."""
    if abs(valor) >= 1:
        texto = f"{valor:,.2f}"
    elif valor == 0:
        texto = "0.0000"
    else:
        # Con 4 decimales fijos un SHIB salia como 0,0000. Van las que hagan
        # falta para 4 cifras, y los ceros sobrantes fuera: 0,00002 y no 0,00002000.
        cifras = -math.floor(math.log10(abs(valor))) + 3
        texto = f"{valor:.{min(max(4, cifras), MAX_DECIMALES)}f}"
        entero, decimales = texto.split(".")
        texto = f"{entero}.{decimales[:4]}{decimales[4:].rstrip('0')}"

    # De formato ingles (1,234.56) a español (1.234,56).
    return texto.replace(",", "@").replace(".", ",").replace("@", ".")
