"""Compara precios con los umbrales y decide si hay que avisar."""

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, time

from .aceite import PRECIO as PRECIO_ACEITE
from .aceite import Aceite
from .adios import Adios
from .adivina import Intento
from .airpods import PRECIO as PRECIO_AIRPODS
from .airpods import Airpods
from .alquiler import PRECIO as PRECIO_ALQUILER
from .alquiler import Alquiler
from .anual import Año
from .ave import PRECIO as PRECIO_AVE
from .ave import Ave
from .avisados import Ultimo
from .ballena import Ballena
from .bici import PRECIO as PRECIO_BICI
from .bici import Bici
from .bigmac import PRECIO as PRECIO_BIGMAC
from .bigmac import BigMac
from .boda import PRECIO as PRECIO_BODA
from .boda import Boda
from .cafe import PRECIO as PRECIO_CAFE
from .cafe import Cafe
from .caida import Caida
from .calendario import Mes
from .cana import PRECIO as PRECIO_CANA
from .cana import Cana
from .caraocruz import QUE_HACER
from .carnet import PRECIO as PRECIO_CARNET
from .carnet import Carnet
from .cartera import Valor, mejor_y_peor, peso
from .churros import PRECIO as PRECIO_CHURROS
from .churros import Churros
from .cine import PRECIO as PRECIO_CINE
from .cine import Cine
from .coche import PRECIO as PRECIO_COCHE
from .coche import Coche
from .comparar import Resultado
from .comparar import media as media_comparar
from .compensar import Compensacion
from .compras import Compra, Resumen
from .concentracion import Concentracion
from .concierto import PRECIO as PRECIO_CONCIERTO
from .concierto import Concierto
from .config import Posicion, Watch
from .corregir import CANTIDAD, Correccion
from .correlacion import Correlacion
from .croquetas import PRECIO as PRECIO_CROQUETAS
from .croquetas import Croquetas
from .cuando import Cuando
from .cumple import Cumple
from .dado import CARAS
from .dado import QUE_HACER as QUE_HACER_DADO
from .dia import Dia
from .diasemana import NOMBRES, DiasSemana
from .doble import Cartera as CarteraDoble
from .emoji import cara as cara_emoji
from .equilibrio import Cartera
from .ethereum import Ethereum
from .frase import Frase
from .futbol import PRECIO as PRECIO_FUTBOL
from .futbol import Futbol
from .galleta import Galleta
from .ganancias import Ganancias
from .gasolina import DEPOSITO, Gasolina
from .gasolina import PRECIO as PRECIO_GASOLINA
from .gimnasio import PRECIO as PRECIO_GIMNASIO
from .gimnasio import Gimnasio
from .glosario import TERMINOS, buscar, parecido
from .halving import Halving
from .hodl import Hodl
from .horas import Horas
from .horoscopo import Horoscopo
from .hotel import PRECIO as PRECIO_HOTEL
from .hotel import Hotel
from .hoy import Hoy
from .hoy import mejor_y_peor as extremos_hoy
from .impuestos import Impuestos
from .iphone import PRECIO as PRECIO_IPHONE
from .iphone import Iphone
from .jamon import PRECIO as PRECIO_JAMON
from .jamon import Jamon
from .kebab import PRECIO as PRECIO_KEBAB
from .kebab import Kebab
from .lambo import PRECIO as PRECIO_LAMBO
from .lambo import Lambo
from .libro import PRECIO as PRECIO_LIBRO
from .libro import Libro
from .loteria import PRECIO as PRECIO_LOTERIA
from .loteria import Loteria
from .luz import PRECIO as PRECIO_LUZ
from .luz import Luz
from .macbook import PRECIO as PRECIO_MACBOOK
from .macbook import Macbook
from .maximo import Maximo, hace
from .media import lado_de_todas
from .mejor import Extremo
from .menu import PRECIO as PRECIO_MENU
from .menu import Menu
from .mercado import Mercado, grande
from .merge import Merge
from .mes import MESES
from .meta import Meta
from .metro import PRECIO as PRECIO_METRO
from .metro import Metro
from .miedo import Indice
from .miedo import hace as dia_miedo
from .miedo import nombre as nombre_miedo
from .millonario import Millonario, cantidad
from .mitad import Cartera as CarteraMitad
from .movimientos import (
    Movimiento,
    descuadre,
    precio_medio,
    recibido,
    texto_cantidad,
    totales,
)
from .mundo import PERSONAS, Mundo
from .navidad import PRECIO as PRECIO_NAVIDAD
from .navidad import Navidad
from .netflix import PRECIO as PRECIO_NETFLIX
from .netflix import Netflix
from .nochevieja import PRECIO as PRECIO_CAVA
from .nochevieja import Nochevieja
from .objetivo import Escenario
from .oro import Oro
from .paella import PRECIO as PRECIO_PAELLA
from .paella import Paella
from .pan import PRECIO as PRECIO_PAN
from .pan import Pan
from .peluqueria import PRECIO as PRECIO_PELUQUERIA
from .peluqueria import Peluqueria
from .periodo import nombre as nombre_periodo
from .piso import METROS as METROS_PISO
from .piso import PRECIO as PRECIO_PISO
from .piso import Piso
from .pizza import BTC, Pizza
from .ppt import EMOJIS as EMOJIS_PPT
from .ppt import QUE_HACER as QUE_HACER_PPT
from .primera import Primera
from .ps5 import PRECIO as PRECIO_PS5
from .ps5 import Ps5
from .puntuales import CARTERA, Puntual, cumplidas, ejemplo, progreso
from .quieta import Quieta
from .racha import Racha
from .rango import Rango, barra
from .ratio import Ratio
from .rebalanceo import EJEMPLO as EJEMPLO_REBALANCEO
from .rebalanceo import Paso
from .record import Record
from .recordar import Recordatorio
from .redondo import Redondo
from .rellenar import Relleno
from .rentabilidad import MIN_DIAS as MIN_DIAS_RENTABILIDAD
from .rentabilidad import Rentabilidad
from .reparto import Trozo, demasiado
from .riesgo import CAIDA as CAIDA_RIESGO
from .riesgo import Riesgo
from .rolex import PRECIO as PRECIO_ROLEX
from .rolex import Rolex
from .rsi import PERIODO, SOBRECOMPRA, SOBREVENTA, Rsi, hasta_zona
from .sat import CANTIDADES as CANTIDADES_SAT
from .sat import SATS_POR_BTC, Sat
from .semanal import Semana
from .sivendo import Simulacion
from .sofa import PRECIO as PRECIO_SOFA
from .sofa import Sofa
from .spotify import PRECIO as PRECIO_SPOTIFY
from .spotify import Spotify
from .stop import Stop
from .sube import Subida
from .sueldo import PAGA as PAGA_SMI
from .sueldo import Sueldo
from .supermercado import PRECIO as PRECIO_SUPER
from .supermercado import Super
from .switch import PRECIO as PRECIO_SWITCH
from .switch import Switch
from .tarot import Carta
from .taxi import PRECIO as PRECIO_TAXI
from .taxi import Taxi
from .telegram import escape
from .tendencias import Tendencia
from .tesla import PRECIO as PRECIO_TESLA
from .tesla import Tesla
from .tiempo import parte as parte_tiempo
from .top import ENTRE, Movida
from .tortilla import PRECIO as PRECIO_TORTILLA
from .tortilla import Tortilla
from .verdes import Verdes
from .version import Version
from .videojuego import PRECIO as PRECIO_VIDEOJUEGO
from .videojuego import Videojuego
from .vsbtc import Contra
from .vuelo import PRECIO as PRECIO_VUELO
from .vuelo import Vuelo
from .whitepaper import Whitepaper
from .zapatillas import PRECIO as PRECIO_ZAPATILLAS
from .zapatillas import Zapatillas

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
    falta_maximo: float | None = None  # en %; 0 si esta en maximos


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
    if alerta.falta_maximo == 0:
        texto += "\n🎉 <i>Está en su máximo histórico</i>"
    elif alerta.falta_maximo is not None:
        texto += (
            f"\n<i>Le falta +{alerta.falta_maximo:.2f}% para su máximo histórico</i>"
        )
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
    mejor, peor = extremos_hoy(lineas) or (None, None)
    for coin_id, h in lineas:
        nombre = escape(coin_id.replace("-", " ").title())
        if h is None:
            texto.append(f"<b>{nombre}</b>  <i>(sin precios de hoy)</i>")
            continue
        linea = f"<b>{nombre}</b>  {simbolo}{_num(h.ahora)}  "
        linea += f"{_flecha(h.cambio)} {h.cambio:+.2f}%"
        if h.desde is not None:
            linea += f" <i>(desde las {h.desde.astimezone():%H:%M})</i>"
        if coin_id == mejor:
            linea += "  <i>← la mejor</i>"
        elif coin_id == peor:
            linea += "  <i>← la peor</i>"
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
    valores: list[Valor],
    total: Valor,
    faltan: list[str],
    currency: str,
    sats: float | None = None,
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
    if sats is not None:
        texto.append(f"<i>En sats: {texto_cantidad(round(sats))}</i>")
    extremos = mejor_y_peor(valores)
    if extremos:
        mejor, peor = (
            f"<b>{escape(v.coin_id.replace('-', ' ').title())}</b> {v.porcentaje:+.2f}%"
            for v in extremos
        )
        texto.append(f"La que mejor va: {mejor} · la que peor: {peor}")

    if faltan:
        # Mejor decir que el total esta cojo que dar uno que parezca completo.
        nombres = ", ".join(escape(c) for c in faltan)
        texto.append(f"<i>Sin precio ahora de: {nombres}. El total no las cuenta.</i>")

    return "\n".join(texto)


def formatear_compra(
    cantidad: float,
    coste: float,
    ahora: Posicion,
    currency: str,
    antes: Posicion | None = None,
    precio: float | None = None,
    comision: float | None = None,
    nota: str | None = None,
) -> str:
    """Lo que se contesta a un /compra: lo apuntado y como queda."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(ahora.coin_id.replace("-", " ").title())
    texto = (
        f"🛒 Apunto <b>{texto_cantidad(cantidad)}</b> de {nombre} "
        f"por {simbolo}{_num(coste)}{_con_comision(comision, simbolo)}.\n"
        f"Ahora tienes {texto_cantidad(ahora.cantidad)}"
    )
    if ahora.invertido is not None:
        texto += f", que te costaron {simbolo}{_num(ahora.invertido)}"
    texto += "."
    # En la primera compra el medio es lo que acabas de pagar, no dice nada.
    medio_antes, medio = precio_medio(antes), precio_medio(ahora)
    if medio_antes is not None and medio is not None:
        texto += (
            f"\n{_flecha(medio - medio_antes)} Te sale a {simbolo}{_num(medio)} "
            f"cada una, antes a {simbolo}{_num(medio_antes)}."
        )
    texto += " Mira /cartera"
    if nota:
        texto += f"\n📝 {escape(nota)}"
    # Sin la comisión: con ella, una compra pequeña parecería una errata.
    raro = descuadre(cantidad, coste - (comision or 0), precio)
    if raro is not None:
        texto += (
            f"\n\n⚠️ Esta la pagas a {simbolo}{_num(coste / cantidad)} cada una y ahora "
            f"está a {simbolo}{_num(precio)} ({raro:+.0f}%). "
            "Si es una errata, dale a Deshacer."
        )
    return texto


def formatear_venta(
    coin_id: str,
    vendido: float,
    queda: Posicion | None,
    currency: str,
    cobrado: float | None = None,
    ganancia: float | None = None,
    comision: float | None = None,
    nota: str | None = None,
) -> str:
    """Lo que se contesta a un /venta. queda es None si ya no tienes nada."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    texto = f"💸 Apunto la venta de <b>{texto_cantidad(vendido)}</b> de {nombre}"
    if cobrado is not None:
        texto += f" por {simbolo}{_num(cobrado)}{_con_comision(comision, simbolo)}"
    texto += ".\n"
    if nota:
        texto += f"📝 {escape(nota)}\n"
    if ganancia is not None:
        texto += f"{_flecha(ganancia)} Le sacas {_ganancia(ganancia, simbolo)}"
        # Si hay ganancia es que hay cobrado: lo que costó es la resta.
        coste = cobrado - ganancia
        if coste > 0:
            texto += f" ({ganancia / coste * 100:+.2f}%)"
        texto += ". Lo de todas, en /ganancias\n"
    if queda is None:
        return texto + f"Ya no te queda nada de {nombre}."

    texto += f"Te quedan {texto_cantidad(queda.cantidad)}"
    if queda.invertido is not None:
        texto += f", que te costaron {simbolo}{_num(queda.invertido)}"
    return texto + ". Mira /cartera"


def _con_comision(comision: float | None, simbolo: str) -> str:
    if not comision:
        return ""
    # _num le pone 4 decimales a lo menor de 1, y "€0,3000" en dinero queda raro.
    if comision >= 0.01:
        texto = f"{comision:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    else:
        texto = _num(comision)
    return f" (con {simbolo}{texto} de comisión)"


def formatear_movimientos(
    lista: list[Movimiento],
    currency: str,
    coin_id: str | None = None,
    todos: list[Movimiento] | None = None,
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
        por = "por"
        if m.tipo == "compra":
            linea = f"🛒 Compra de {texto_cantidad(m.cantidad)} de {nombre}"
        elif m.tipo == "recompensa":
            linea = f"🎁 Recompensa de {texto_cantidad(m.cantidad)} de {nombre}"
            por = "que valía"
        else:
            linea = f"💸 Venta de {texto_cantidad(m.cantidad)} de {nombre}"
        if m.coste is not None:
            linea += f" {por} {simbolo}{_num(m.coste)}"
            if m.cantidad > 0:
                linea += f" <i>(a {simbolo}{_num(m.coste / m.cantidad)})</i>"
        lineas.append(f"{linea}  <i>{cuando:%d/%m %H:%M} · #{m.id}</i>")
        if m.nota:
            lineas.append(f"      📝 {escape(m.nota)}")

    todos = todos or lista
    comprado, vendido = totales(todos)
    if comprado or vendido:
        de_cuantos = f" de los {len(todos)}" if len(todos) > len(lista) else ""
        lineas.append(
            f"\nEn total{de_cuantos}: {simbolo}{_num(comprado)} comprado · "
            f"{simbolo}{_num(vendido)} vendido"
        )
    regalado = recibido(todos)
    if regalado:
        lineas.append(f"🎁 {simbolo}{_num(regalado)} en recompensas")
    return "\n".join(lineas)


def formatear_corregido(c: Correccion, currency: str) -> str:
    """Lo que se contesta a un /corregir: qué cambia y como queda."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    m = c.despues
    nombre = escape(m.coin_id.replace("-", " ").title())
    if c.campo == CANTIDAD:
        cambio = (
            f"Cantidad: {texto_cantidad(c.antes.cantidad)} → "
            f"<b>{texto_cantidad(m.cantidad)}</b>"
        )
    else:
        antes = (
            "sin apuntar"
            if c.antes.coste is None
            else f"{simbolo}{_num(c.antes.coste)}"
        )
        cambio = f"Importe: {antes} → <b>{simbolo}{_num(m.coste)}</b>"

    lineas = [f"✏️ Corrijo la {m.tipo} <b>#{m.id}</b> de {nombre}.", cambio]
    if c.rehechos:
        cuantos = (
            "el movimiento que va detrás"
            if c.rehechos == 1
            else f"los {c.rehechos} movimientos que van detrás"
        )
        lineas.append(f"He rehecho las cuentas de {cuantos}.")
    if c.final is None:
        lineas.append(f"Ya no te queda nada de {nombre}. Mira /cartera")
    else:
        queda = f"Ahora tienes {texto_cantidad(c.final.cantidad)}"
        if c.final.invertido is not None:
            queda += f", que te costaron {simbolo}{_num(c.final.invertido)}"
        lineas.append(f"{queda}. Mira /cartera")
    return "\n".join(lineas)


def formatear_recompensa(
    cantidad: float,
    valor: float,
    ahora: Posicion,
    currency: str,
    nota: str | None = None,
) -> str:
    """Lo que se contesta a un /recompensa: lo apuntado y como queda."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(ahora.coin_id.replace("-", " ").title())
    texto = (
        f"🎁 Apunto <b>{texto_cantidad(cantidad)}</b> de {nombre} de recompensa, "
        f"valorada en {simbolo}{_num(valor)}.\n"
        f"Ahora tienes {texto_cantidad(ahora.cantidad)}. Mira /cartera"
    )
    if nota:
        texto += f"\n📝 {escape(nota)}"
    return (
        texto + "\n<i>Lo sumo a lo que te costó: al venderla, solo cuenta como "
        "ganancia lo que suba desde que te llegó.</i>"
    )


def formatear_hodl(lista: list[Hodl], sin_fecha: list[str], hoy: date) -> str:
    """Respuesta de /hodl."""
    texto = ["💎 <b>Lo que llevas sin vender</b>", ""]
    for h in lista:
        nombre = escape(h.coin_id.replace("-", " ").title())
        dias = h.dias(hoy)
        cuanto = (
            "hoy"
            if dias == 0
            else _es(f"{dias:,}") + (" día" if dias == 1 else " días")
        )
        if h.minimo:
            cuanto = f"más de {cuanto}"
        fecha = f"{h.desde.astimezone():%d/%m/%Y}"
        if h.venta:
            de_cuando = f"desde que vendiste un poco el {fecha}"
        elif h.minimo:
            de_cuando = f"ya la tenías antes de apuntar la compra del {fecha}"
        else:
            de_cuando = f"desde la compra del {fecha}"
        texto.append(f"<b>{nombre}</b>  {cuanto}")
        texto.append(f"   <i>{de_cuando}</i>")
    if sin_fecha:
        nombres = ", ".join(escape(c.replace("-", " ").title()) for c in sin_fecha)
        texto.append(
            f"\n<i>De {nombres} no sé desde cuándo la tienes: viene del .env y "
            "no has apuntado ninguna compra</i>"
        )
    return "\n".join(texto)


def formatear_record(r: Record, currency: str) -> str:
    """Respuesta de /record."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    cuando = r.cuando.astimezone()
    texto = ["🏆 <b>El récord de tu cartera</b>"]
    if r.en_record:
        texto.append(f"🎉 Lo tienes ahora mismo: <b>{simbolo}{_num(r.ahora)}</b>")
    else:
        texto.append(
            f"<b>{simbolo}{_num(r.maximo)}</b>, el {cuando:%d/%m/%Y a las %H:%M}"
        )
        texto.append(
            f"Ahora vale {simbolo}{_num(r.ahora)}: 🔻 {r.caida:.2f}%, "
            f"le faltan <b>{simbolo}{_num(r.falta)}</b> para volver"
        )
    # No sé lo que tenías cada día: es lo de hoy a los precios de entonces.
    texto.append(
        f"<i>Con lo que tienes hoy y los precios que guardo desde el "
        f"{r.desde.astimezone():%d/%m/%Y}</i>"
    )
    return "\n".join(texto)


def formatear_bajon(r: Record, escalon: int, porcentaje: float, currency: str) -> str:
    """El aviso de CAIDA_CARTERA."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    caida = f"{-r.caida:.1f}".replace(".", ",")
    texto = [
        f"📉 <b>Tu cartera ha caído un {caida}% desde su récord</b>",
        f"De {simbolo}{_num(r.maximo)} el {r.cuando.astimezone():%d/%m/%Y} "
        f"a <b>{simbolo}{_num(r.ahora)}</b> ahora",
        f"Le faltan {simbolo}{_num(r.falta)} para volver",
        f"<i>Ya pasa del {_pct(escalon * porcentaje)}%. "
        f"El siguiente aviso, al {_pct((escalon + 1) * porcentaje)}%</i>",
    ]
    return "\n".join(texto)


def formatear_concentracion(c: Concentracion) -> str:
    """El aviso de CONCENTRACION."""
    nombre = escape(c.coin_id.replace("-", " ").title())
    si_cae = f"{c.si_cae:.1f}".replace(".", ",").removesuffix(",0")
    return "\n".join(
        [
            f"⚖️ <b>{nombre} ya es el {c.peso:.0f}% de tu cartera</b>",
            f"Si cae un {CAIDA_RIESGO}%, tu cartera cae un {si_cae}%.",
            "Cuánto se mueve todo junto, en /riesgo. Qué mover para repartirlo, "
            "en /rebalanceo",
        ]
    )


def formatear_aviso_rsi(coin_id: str, r: Rsi, currency: str) -> str:
    """El aviso de AVISO_RSI."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    if r.valor >= SOBRECOMPRA:
        cabecera = "🔥 <b>{} está sobrecomprada</b>"
        detalle = "Ha subido mucho y rápido, suele frenar."
    else:
        cabecera = "🧊 <b>{} está sobrevendida</b>"
        detalle = "Ha bajado mucho y rápido, suele rebotar."
    return "\n".join(
        [
            cabecera.format(nombre),
            f"RSI de {PERIODO} días: <b>{r.valor:.0f}</b>. {detalle}",
            f"Ahora {simbolo}{_num(r.ahora)}",
            f"El detalle, en /rsi {escape(coin_id)}",
        ]
    )


def _veces(n: int, una: str, varias: str) -> str:
    return f"{n} {una if n == 1 else varias}"


def formatear_anual(a: Año, currency: str, hoy: date) -> str:
    """El resumen del año: el 1 de enero, o con /anual 2025."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    hasta_hoy = " hasta hoy" if a.año == hoy.year else ""
    if a.cartera is None and not a.compras and not a.ventas:
        return (
            f"De {a.año}{hasta_hoy} no tengo nada: ni precios guardados de tu "
            "cartera ni compras o ventas apuntadas por aquí."
        )

    lineas = [f"🎆 <b>Tu {a.año} en cripto{hasta_hoy}</b>", ""]
    c = a.cartera
    if c is not None:
        cambio = (
            f" {_flecha(c.ganancia)} {_signo(c.porcentaje)}" if c.porcentaje else ""
        )
        lineas.append(
            f"💼 Tu cartera: de {simbolo}{_num(c.inicio)} a "
            f"<b>{simbolo}{_num(c.fin)}</b>{cambio} ({_ganancia(c.ganancia, simbolo)})"
        )
        if len(c.cambios) > 1:
            (mejor, sube), (peor, baja) = c.cambios[0], c.cambios[-1]
            lineas.append(
                f"🥇 La que mejor, {_nombre(mejor)}: {_signo(sube)}. "
                f"La que peor, {_nombre(peor)}: {_signo(baja)}"
            )
        if a.mejor_mes and a.peor_mes:
            (bueno, sube), (malo, baja) = a.mejor_mes, a.peor_mes
            lineas.append(
                f"📅 Mejor mes, {MESES[bueno - 1]}: {_signo(sube)}. "
                f"Peor, {MESES[malo - 1]}: {_signo(baja)}"
            )

    if a.compras or a.ventas:
        lineas.append("")
        lineas.append(
            f"🛒 {_veces(a.compras, 'compra', 'compras')} por "
            f"{simbolo}{_num(a.comprado)} · 💸 {_veces(a.ventas, 'venta', 'ventas')} "
            f"por {simbolo}{_num(a.vendido)}"
        )
    if a.ventas:
        lineas.append(
            f"💰 Vendiendo, {_ganancia(a.ganado, simbolo)}. El detalle, en "
            f"/impuestos {a.año}"
        )
    r = a.mis_compras
    if r is not None:
        fin = "hoy" if hasta_hoy else "a fin de año"
        lineas.append(f"⭐ Tu mejor compra: {_compra_corta(r.mejor)}, {fin}")
        if r.total > 1:
            lineas.append(f"🥴 La peor: {_compra_corta(r.peor)}")

    lineas.append("")
    if c is not None:
        lineas.append(
            "<i>La cartera es lo que tienes hoy, a los precios de cada día.</i>"
        )
    # Si purgas el histórico o empezaste a medio año, que se sepa de dónde sale.
    if a.desde and a.desde > date(a.año, 1, 2):
        lineas.append(
            f"<i>Solo tengo precios desde el {a.desde:%d/%m}. Para guardar el año "
            "entero, HISTORY_DAYS=366 en el .env.</i>"
        )
    return "\n".join(lineas).rstrip()


def _compra_corta(c: Compra) -> str:
    m = c.movimiento
    return (
        f"{texto_cantidad(m.cantidad)} de {_nombre(m.coin_id)} el "
        f"{m.cuando.astimezone():%d/%m}, {_flecha(c.cambio)} {_signo(c.cambio)}"
    )


def formatear_riesgo(r: Riesgo, currency: str) -> str:
    """Respuesta de /riesgo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(r.mayor.replace("-", " ").title())
    texto = ["🎯 <b>El riesgo de tu cartera</b>", ""]

    if r.cuantas == 1:
        texto.append(
            f"Todo lo que tienes es <b>{nombre}</b>: lo que haga, lo hace tu cartera"
        )
    else:
        texto.append(
            f"<b>{nombre}</b> es el {r.peso:.0f}% de lo que tienes: si cae un "
            f"{CAIDA_RIESGO}%, tu cartera cae un {_decimal(r.si_cae)}%"
        )
        texto.append(
            f"Con {r.cuantas} criptos, es como tener {_decimal(r.equivalentes)} "
            "a partes iguales"
        )

    texto.append("")
    if r.movimiento is None:
        texto.append(
            "Aún no tengo dos días de precios de tu cartera para saber cuánto se "
            "mueve. Vuelve mañana."
        )
        return "\n".join(texto)

    m = r.movimiento
    media = f"{m.media:.1f}".replace(".", ",")
    peor = f"{m.peor:+.1f}".replace(".", ",")
    euros = f"{simbolo}{_num(r.al_dia)}"
    texto.append(f"📊 Se mueve de media un {media}% al día: unos <b>{euros}</b>")
    # Es el que más se movió, para arriba o para abajo: "peor" engañaría en una subida.
    texto.append(f"Su día más movido, el {m.peor_dia:%d/%m}: {_flecha(m.peor)} {peor}%")
    if r.contra_btc:
        btc = f"{r.btc:.1f}".replace(".", ",")
        texto.append(f"Se mueve {r.contra_btc} que bitcoin ({btc}%)")

    icono = {"bajo": "🟢", "medio": "🟠", "alto": "🔴"}[r.nivel]
    texto += ["", f"{icono} Riesgo {r.nivel}"]
    texto.append(f"<i>Con los precios de los últimos {m.dias + 1} días</i>")
    return "\n".join(texto)


def _decimal(valor: float) -> str:
    """1,5 o 3: un decimal, y sin él si es redondo."""
    return f"{valor:.1f}".replace(".", ",").removesuffix(",0")


def formatear_calendario(coin_id: str, m: Mes) -> str:
    """El pie de /calendario, y lo que va si la imagen no sale."""
    nombre = escape(coin_id.replace("-", " ").title())
    texto = [f"🗓 <b>{nombre} en {MESES[m.mes - 1]} de {m.año}</b>", ""]
    if not m.con_dato:
        texto.append(
            "No tengo dos días seguidos con precio en este mes. Solo sé de las que "
            "vigilo, y desde que las vigilo."
        )
        return "\n".join(texto)

    dias = "1 día" if m.verdes == 1 else f"{m.verdes} días"
    texto.append(f"🟩 {dias} en verde · 🟥 {m.rojos} en rojo")
    for titulo, c in (("Mejor", m.mejor), ("Peor", m.peor)):
        pct = f"{c.cambio:+.1f}".replace(".", ",")
        texto.append(f"{titulo}, el {c.dia.day}: {_flecha(c.cambio)} {pct}%")
    if m.cambio is not None:
        pct = f"{m.cambio:+.1f}".replace(".", ",")
        texto.append(f"En el mes: {_flecha(m.cambio)} {pct}%")

    sin = sum(1 for c in m.casillas if not c.futuro and c.cambio is None)
    if sin:
        cuantos = "1 día sin precio" if sin == 1 else f"{sin} días sin precio"
        texto.append(f"<i>{cuantos}, o sin el del día anterior: van en gris</i>")
    return "\n".join(texto)


def formatear_rentabilidad(r: Rentabilidad, currency: str) -> str:
    """Respuesta de /rentabilidad."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    if r.sacado:
        dinero = [
            f"Has metido {simbolo}{_num(r.metido)} y sacado {simbolo}{_num(r.sacado)}",
            f"Lo que te queda vale {simbolo}{_num(r.vale)}",
        ]
    else:
        dinero = [
            f"Has metido {simbolo}{_num(r.metido)}. Hoy vale {simbolo}{_num(r.vale)}"
        ]

    if r.dias == 0:
        tiempo = "hoy"
    elif r.dias == 1:
        tiempo = "en 1 día"
    else:
        tiempo = f"en {r.dias:,} días".replace(",", ".")
    verbo = "Ganas" if r.ganancia >= 0 else "Pierdes"
    pct = f"{r.porcentaje:+.1f}".replace(".", ",")
    texto = [
        "📈 <b>Tu rentabilidad</b>",
        "",
        *dinero,
        f"{_flecha(r.ganancia)} {verbo} <b>{_ganancia(r.ganancia, simbolo)}</b> "
        f"({pct}%) {tiempo}",
    ]

    if r.anual is not None:
        anual = f"{r.anual:+,.1f}".replace(",", "@").replace(".", ",").replace("@", ".")
        texto.append(f"📅 Al año, un <b>{anual}%</b>")
        texto.append(
            "<i>Cuenta cuándo metiste y sacaste cada euro: no es lo mismo un 10% "
            "en un mes que en tres años</i>"
        )
    elif r.dias < MIN_DIAS_RENTABILIDAD:
        texto.append(
            "<i>Con menos de un mes no lo paso a anual: una buena semana saldría "
            "como un +1.000% al año</i>"
        )

    if r.fuera:
        cuantos = (
            "1 movimiento no cuenta"
            if r.fuera == 1
            else (f"{r.fuera} movimientos no cuentan")
        )
        texto.append(
            f"<i>{cuantos}: sin precio, o ventas de lo que tenías en el .env</i>"
        )
    return "\n".join(texto)


def formatear_compras(r: Resumen, currency: str, coin_id: str | None) -> str:
    """Respuesta de /compras."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    de = f" de {escape(coin_id.replace('-', ' ').title())}" if coin_id else ""
    texto = [f"🧾 <b>Tus compras{de}</b>", ""]

    if r.total == 1:
        texto += _una_compra("📌 Solo tienes una compra", r.mejor, simbolo)
    else:
        texto += _una_compra("🥇 La mejor", r.mejor, simbolo)
        texto.append("")
        texto += _una_compra("🥴 La peor", r.peor, simbolo)
        texto.append("")
        if not r.rojas:
            texto.append(f"De {r.total} compras, las {r.total} van ganando")
        elif not r.verdes:
            texto.append(f"De {r.total} compras, las {r.total} van perdiendo")
        else:
            texto.append(
                f"De {r.total} compras, {r.verdes} van ganando y {r.rojas} perdiendo"
            )

    if r.sin_precio:
        cuantas = "1 sin" if r.sin_precio == 1 else f"{r.sin_precio} sin"
        cuenta = "no cuenta" if r.sin_precio == 1 else "no cuentan"
        texto.append(f"<i>{cuantas} lo que costó o sin precio de hoy, {cuenta}</i>")
    cada = "A precio de hoy" if r.total == 1 else "Cada una a precio de hoy"
    texto.append(f"<i>{cada}, aunque ya la hayas vendido</i>")
    return "\n".join(texto)


def _una_compra(titulo: str, c: Compra, simbolo: str) -> list[str]:
    m = c.movimiento
    nombre = escape(m.coin_id.replace("-", " ").title())
    cambio = f"{c.cambio:+.1f}".replace(".", ",")
    lineas = [
        f"{titulo}: {texto_cantidad(m.cantidad)} de {nombre} el "
        f"{m.cuando.astimezone():%d/%m/%Y} a {simbolo}{_num(c.pagado)}",
        f"{_flecha(c.cambio)} {cambio}%, <b>{_ganancia(c.ganancia, simbolo)}</b>",
    ]
    # Lo que pensabas al comprar al lado de cómo ha salido: para eso se apunta.
    if m.nota:
        lineas.append(f"📝 {escape(m.nota)}")
    return lineas


def formatear_vsbtc(c: Contra, currency: str) -> str:
    """Respuesta de /vsbtc."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🥊 <b>Tu cartera contra bitcoin</b>",
        f"Lo que compraste vale hoy <b>{simbolo}{_num(c.real)}</b>",
        f"Con ese dinero en bitcoin, en las mismas fechas, tendrías "
        f"{texto_cantidad(c.sats)} BTC: {simbolo}{_num(c.btc)}",
        "",
    ]
    # Por debajo de un céntimo son restos de los decimales: cuenta como empate.
    if abs(c.diferencia) < 0.01 or c.ventaja is None:
        texto.append("🤝 Vas igual que bitcoin")
    else:
        pct = f"{c.ventaja:+.1f}".replace(".", ",")
        diferencia = f"<b>{simbolo}{_num(abs(c.diferencia))}</b> ({pct}%)"
        if c.diferencia > 0:
            texto.append(f"🏆 Le ganas a bitcoin por {diferencia}")
        else:
            texto.append(f"🟠 Bitcoin te gana por {diferencia}")

    pie = f"Con tus compras y ventas desde el {c.desde.astimezone():%d/%m/%Y}"
    if c.fuera == 1:
        pie += ". 1 movimiento no cuenta: sin precio o sin bitcoin guardado de ese día"
    elif c.fuera:
        pie += (
            f". {c.fuera} movimientos no cuentan: sin precio o sin bitcoin "
            "guardado de ese día"
        )
    texto.append(f"<i>{pie}</i>")
    return "\n".join(texto)


def _pct(valor: float) -> str:
    return f"{valor:g}".replace(".", ",")


def formatear_primera(p: Primera, currency: str) -> str:
    """Respuesta de /primera."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    m = p.compra
    nombre = escape(m.coin_id.replace("-", " ").title())
    linea = f"{texto_cantidad(m.cantidad)} de {nombre}"
    if m.coste is not None:
        linea += f" por {simbolo}{_num(m.coste)}"
        if p.pagado is not None:
            linea += f" (a {simbolo}{_num(p.pagado)})"
    if p.dias == 0:
        hace = "hoy"
    elif p.dias == 1:
        hace = "hace 1 día"
    else:
        hace = f"hace {p.dias:,} días".replace(",", ".")
    texto = [
        "🥇 <b>Tu primera compra</b>",
        linea,
        f"<i>el {m.cuando.astimezone():%d/%m/%Y}, {hace}</i>",
    ]

    if p.precio is None:
        return "\n".join(texto)
    if p.cambio is not None:
        texto.append(
            f"\n{_flecha(p.cambio)} Ahora está a {simbolo}{_num(p.precio)}: "
            f"<b>{p.cambio:+.2f}%</b> desde entonces"
        )
    else:
        texto.append(f"\nAhora está a {simbolo}{_num(p.precio)}")
    valor = m.cantidad * p.precio
    linea = f"Lo que compraste vale hoy {simbolo}{_num(valor)}"
    if m.coste is not None:
        linea += f" ({_ganancia(valor - m.coste, simbolo)})"
    texto.append(linea)
    return "\n".join(texto)


def formatear_ganancias(g: Ganancias, currency: str) -> str:
    """Respuesta de /ganancias: lo que has sacado de verdad, sin lo que aún tienes."""
    if not g.por_cripto and not g.sin_datos:
        return (
            "Todavía no has vendido nada, así que no has ganado ni perdido. "
            "Lo que vale lo que tienes sale en /cartera"
        )
    if not g.por_cripto:
        return (
            "Tus ventas apuntadas son de antes de guardar a cuánto vendías, "
            "o de algo sin lo que te costó, así que no puedo sacar cuentas. "
            "Las nuevas ya sí: /venta bitcoin 0.005 350"
        )

    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    lineas = ["💰 <b>Lo que has ganado vendiendo</b>", ""]
    for coin_id, ganancia in g.por_cripto:
        nombre = escape(coin_id.replace("-", " ").title())
        linea = f"{_flecha(ganancia)} <b>{nombre}</b>  {_ganancia(ganancia, simbolo)}"
        porcentaje = g.porcentaje(coin_id)
        if porcentaje is not None:
            linea += f"  <i>{porcentaje:+.2f}%</i>"
        lineas.append(linea)
    if len(g.por_cripto) > 1:
        linea = f"\nTotal <b>{_ganancia(g.total, simbolo)}</b>"
        if g.porcentaje_total is not None:
            linea += f"  <i>{g.porcentaje_total:+.2f}%</i>"
        lineas.append(linea)
    if g.sin_datos:
        cuantas = "1 venta" if g.sin_datos == 1 else f"{g.sin_datos} ventas"
        lineas.append(
            f"<i>No cuento {cuantas}: sin a cuánto vendiste o sin lo que te costó.</i>"
        )
    lineas.append("\nLo que aún tienes no entra, eso está en /cartera")
    return "\n".join(lineas)


def formatear_impuestos(i: Impuestos, currency: str, recibido: float = 0.0) -> str:
    """Respuesta de /impuestos. recibido es lo que valían las recompensas del año."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    recompensas = (
        f"🎁 Recibiste {simbolo}{_num(recibido)} en recompensas: también tributan, "
        "y esto no las suma."
        if recibido
        else ""
    )
    if not i.ventas:
        if recompensas:
            return f"En {i.año} no has vendido nada.\n{recompensas}"
        return f"En {i.año} no has vendido nada, así que no hay nada que declarar."
    if i.ventas == i.sin_datos:
        texto = (
            f"Tus ventas de {i.año} no dicen a cuánto vendiste o lo que te costó, "
            "así que no puedo sacar cuentas."
        )
        return f"{texto}\n{recompensas}" if recompensas else texto

    lineas = [f"🏛️ <b>Impuestos de {i.año}</b>", ""]
    if i.ganancia <= 0:
        lineas.append(f"Vendiendo has perdido <b>{_ganancia(i.ganancia, simbolo)}</b>")
        lineas.append(
            "No pagas nada, y esa pérdida la puedes restar de lo que ganes "
            "los próximos 4 años."
        )
    else:
        lineas.append(f"Has ganado vendiendo <b>{_ganancia(i.ganancia, simbolo)}</b>")
        lineas.append("")
        for tipo, base, cuota in i.tramos:
            lineas.append(f"Al {tipo}%: {simbolo}{_num(base)} → {simbolo}{_num(cuota)}")
        lineas.append(
            f"\n💸 A Hacienda, unos <b>{simbolo}{_num(i.total)}</b>  "
            f"<i>({i.tipo_medio:.2f}% de media)</i>"
        )

    if recompensas:
        lineas.append(f"\n{recompensas}")
    if i.sin_datos:
        cuantas = "1 venta" if i.sin_datos == 1 else f"{i.sin_datos} ventas"
        lineas.append(f"<i>No cuento {cuantas}: les falta el precio.</i>")
    if currency.lower() != "eur":
        lineas.append(
            f"<i>Ojo: va en {currency.upper()}, y Hacienda lo quiere en euros.</i>"
        )
    lineas.append(
        "\n<i>Es orientativo. Va con FIFO, como Hacienda (lo primero que compras "
        "es lo primero que vendes), y /ganancias con precio medio: pueden no "
        "coincidir.</i>"
    )
    return "\n".join(lineas)


def _sivendo_hacienda(s: Simulacion, simbolo: str) -> str:
    if s.hacienda > 0:
        return f"💸 A Hacienda, unos <b>{simbolo}{_num(s.hacienda)}</b>"
    if s.hacienda < 0:
        return (
            f"💸 Te ahorrarías unos <b>{simbolo}{_num(-s.hacienda)}</b> de Hacienda: "
            "esa pérdida se resta de lo que ya has ganado este año."
        )
    if s.ganancia > 0:
        return "💸 A Hacienda, nada: lo tapan las pérdidas que ya llevas este año."
    return (
        "💸 A Hacienda, nada. Si pierdes, lo puedes restar de lo que ganes los "
        "próximos 4 años."
    )


def formatear_compensar(c: Compensacion, currency: str, hoy: date) -> str:
    """Respuesta de /compensar."""
    if c.ganancia <= 0:
        return (
            f"En {c.año} no llevas ganancia vendiendo, así que no hay nada que "
            "compensar. Míralo en /impuestos"
        )

    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    lineas = [
        f"🧾 <b>Compensar pérdidas de {c.año}</b>",
        "",
        f"Llevas ganado vendiendo <b>{_ganancia(c.ganancia, simbolo)}</b>: "
        f"a Hacienda, unos {simbolo}{_num(c.antes)}",
        "",
    ]
    if not c.ventas:
        lineas.append(
            "Nada de tu cartera va en pérdidas, así que no tienes de dónde compensar."
        )
    for v in c.ventas:
        nombre = escape(v.coin_id.replace("-", " ").title())
        cuanto = texto_cantidad(v.cantidad)
        cuanto = f"todo ({cuanto})" if v.todo else cuanto
        lineas.append(
            f"🔻 <b>{nombre}</b>: vende {cuanto} a {simbolo}{_num(v.precio)} "
            f"y pierdes {simbolo}{_num(v.perdida)}"
        )

    if c.ventas:
        lineas.append(f"\n💸 Te ahorrarías unos <b>{simbolo}{_num(c.ahorro)}</b>")
        if c.queda >= 0.01:
            lineas.append(f"Seguirías tributando por {_ganancia(c.queda, simbolo)}")
        dias = (date(c.año + 1, 1, 1) - hoy).days
        lineas.append(
            f"Tiene que ser antes del 1 de enero: "
            f"{'queda 1 día' if dias == 1 else f'quedan {dias} días'}"
        )

    if c.sin_mirar:
        nombres = ", ".join(
            escape(coin_id.replace("-", " ").title()) for coin_id in c.sin_mirar
        )
        lineas.append(f"\n<i>De {nombres} me falta el precio o lo que te costó.</i>")
    if c.sin_datos:
        cuantas = "1 venta" if c.sin_datos == 1 else f"{c.sin_datos} ventas"
        lineas.append(f"<i>No cuento {cuantas} de este año: les falta el precio.</i>")
    if currency.lower() != "eur":
        lineas.append(
            f"<i>Ojo: va en {currency.upper()}, y Hacienda lo quiere en euros.</i>"
        )
    lineas.append(
        "\n<i>No apunto nada. Es orientativo, con FIFO, al precio de ahora y sin "
        "comisiones. Si vas a recomprar enseguida, pregúntale antes a tu gestor: "
        "Hacienda puede no admitir esa pérdida.</i>"
    )
    return "\n".join(lineas)


def formatear_rellenar(
    hechos: list[Relleno], fallos: list[tuple[str, str]], dias: int
) -> str:
    """Respuesta de /rellenar."""
    lineas = [f"🧩 <b>Precios de los últimos {dias} días</b>", ""]
    for r in hechos:
        nombre = escape(r.coin_id.replace("-", " ").title())
        if r.desde is None:
            lineas.append(f"{nombre}: ya lo tenía todo")
            continue
        cuantos = f"{r.nuevos:,}".replace(",", ".")
        nuevos = "precio nuevo" if r.nuevos == 1 else "precios nuevos"
        lineas.append(
            f"{nombre}: <b>{cuantos}</b> {nuevos}, "
            f"desde el {r.desde.astimezone():%d/%m/%Y}"
        )
    for coin_id, error in fallos:
        lineas.append(f"{escape(coin_id)}: no he podido. {escape(error)}")
    return "\n".join(lineas)


def formatear_sivendo(s: Simulacion, currency: str) -> str:
    """Respuesta de /sivendo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(s.coin_id.replace("-", " ").title())
    lineas = [
        f"🤔 <b>Si vendes {texto_cantidad(s.vendido)} de {nombre}</b>",
        "",
        f"Te darían {simbolo}{_num(s.cobrado)}  "
        f"<i>(a {simbolo}{_num(s.cobrado / s.vendido)} cada una)</i>",
    ]
    if s.ganancia is None:
        lineas.append("No sé lo que te costó, así que no puedo sacar lo que ganarías.")
    else:
        ganado = (
            f"{_flecha(s.ganancia)} Le sacarías <b>{_ganancia(s.ganancia, simbolo)}</b>"
        )
        if s.porcentaje is not None:
            ganado += f" ({s.porcentaje:+.2f}%)"
        lineas += [f"Te costó {simbolo}{_num(s.coste)}", ganado]
        if s.ya_ganado:
            lineas.append(
                f"Este año ya llevas {_ganancia(s.ya_ganado, simbolo)} vendiendo"
            )
        lineas += ["", _sivendo_hacienda(s, simbolo)]

    if s.queda:
        lineas.append(f"Te quedarían {texto_cantidad(s.queda)}")
    else:
        lineas.append(f"No te quedaría nada de {nombre}")

    if s.sin_datos:
        cuantas = "1 venta" if s.sin_datos == 1 else f"{s.sin_datos} ventas"
        lineas.append(f"<i>No cuento {cuantas} de este año: les falta el precio.</i>")
    if currency.lower() != "eur":
        lineas.append(
            f"<i>Ojo: va en {currency.upper()}, y Hacienda lo quiere en euros.</i>"
        )
    lineas.append("\n<i>No apunto nada. Es orientativo, con FIFO y sin comisiones.</i>")
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
    variacion: float | None = None,
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
    texto += "</i>"
    # Si escribes dinero, lo que cambia es la cripto que te dan, no lo que vale.
    if variacion is None or desde_dinero:
        return texto
    antes = dinero / (1 + variacion / 100)
    return (
        f"{texto}\nHace 24 h valía {simbolo}{_num(antes)}  "
        f"{_flecha(variacion)} {variacion:+.2f}%"
    )


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
    lado = lado_de_todas(ahora, medias)
    if lado is not None:
        lineas.append(
            "\n🟢 Por encima de todas: va hacia arriba"
            if lado
            else "\n🔴 Por debajo de todas: va hacia abajo"
        )
    lineas.append("\n<i>Con el precio del final de cada día</i>")
    return "\n".join(lineas)


def formatear_racha(
    coin_id: str,
    r: Racha,
    currency: str,
    record: int | None = None,
    desde: date | None = None,
) -> str:
    """Respuesta de /racha. record es la más larga hacia ese lado desde ese día."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    cartera = coin_id == CARTERA
    nombre = "Tu cartera" if cartera else escape(coin_id.replace("-", " ").title())
    hacia = "subiendo" if r.sube else "bajando"
    dias = "1 día" if r.dias == 1 else f"{r.dias} días"
    # Si los datos se acaban antes que la racha, puede ser más larga.
    cuantos = dias if r.entera else f"al menos {dias}"
    texto = (
        f"{_flecha(r.cambio)} <b>{nombre}</b> lleva <b>{cuantos}</b> "
        f"{'' if r.dias == 1 else 'seguidos '}{hacia}, contando hoy\n"
        f"{r.cambio:+.2f}% desde el {r.desde:%d/%m}: "
        f"{simbolo}{_num(r.antes)} → {simbolo}{_num(r.ahora)}\n"
    )
    if r.dias > 1:
        texto += f"De media, {r.al_dia:+.2f}% al día\n"
    # Si no sé dónde empieza la de ahora, compararla con otra no vale.
    if r.entera and record and desde:
        if record <= r.dias:
            texto += f"🏆 Es la más larga {hacia} desde el {desde:%d/%m}\n"
        else:
            texto += (
                f"La más larga {hacia} desde el {desde:%d/%m} fue de {record} días\n"
            )
    if cartera:
        return texto + "<i>Con lo que tienes hoy, al precio del final de cada día</i>"
    return texto + "<i>Con el precio del final de cada día</i>"


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
        puntos, arriba = hasta_zona(r.valor)
        cuantos = "menos de 1 punto" if puntos < 1 else f"{puntos:.0f} puntos"
        zona += (
            f"\nLe faltan {cuantos} para "
            f"{'sobrecomprada' if arriba else 'sobrevendida'}"
        )

    texto = (
        f"📊 <b>{nombre}</b>, RSI de {PERIODO} días: <b>{r.valor:.0f}</b>\n"
        f"<code>0 {barra(r.valor)} 100</code>\n"
        f"{zona}\n"
        f"{_rsi_antes(r)}\n"
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


def _rsi_antes(r: Rsi) -> str:
    if r.hace_semana is None:
        return ""
    antes, ahora = round(r.hace_semana), round(r.valor)
    if antes == ahora:
        return "Igual que hace una semana\n"
    rumbo = "subiendo ↗️" if ahora > antes else "bajando ↘️"
    return f"Hace una semana {antes}, va {rumbo}\n"


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
            f"Ahora {simbolo}{_num(c.ahora)}\n"
            f"Tendría que {'bajar' if c.por_debajo else 'subir'} un "
            f"<b>{abs(c.falta):.2f}%</b> para llegar"
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


def formatear_lambo(lambo: Lambo, currency: str) -> str:
    """Respuesta de /lambo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🏎️ <b>Tu cartera en Lamborghinis</b>",
        f"Vale {simbolo}{_num(lambo.valor)}",
    ]
    if lambo.enteros == 0:
        texto.append(f"Te da para el <b>{lambo.parte:.2f}%</b> de uno")
        siguiente = "el primero"
    else:
        cuantos = f"{lambo.enteros} Lamborghini{'s' if lambo.enteros > 1 else ''}"
        texto.append(f"Te da para <b>{cuantos}</b> 🎉")
        siguiente = "el siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(lambo.falta)}")
    precio = f"{PRECIO_LAMBO:,}".replace(",", ".")
    texto.append(f"<i>A unos {simbolo}{precio} cada uno</i>")
    return "\n".join(texto)


def formatear_cafe(cafe: Cafe, currency: str) -> str:
    """Respuesta de /cafe."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["☕ <b>Tu cartera en cafés</b>", f"Vale {simbolo}{_num(cafe.valor)}"]
    if cafe.cuantos == 0:
        texto.append("No te da ni para un café 😅")
    else:
        cuantos = f"{cafe.cuantos:,}".replace(",", ".")
        texto.append(
            f"Te da para <b>{cuantos} café{'s' if cafe.cuantos > 1 else ''}</b>"
        )
        if cafe.años >= 1:
            para = f"{cafe.años:.1f} años".replace(".", ",")
        else:
            para = "1 día" if cafe.cuantos == 1 else f"{cafe.cuantos} días"
        texto.append(f"Uno al día, tienes para {para}")
    texto.append(f"<i>A {simbolo}{_num(PRECIO_CAFE)} cada uno</i>")
    return "\n".join(texto)


def formatear_cana(c: Cana, currency: str) -> str:
    """Respuesta de /cana."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🍺 <b>Tu cartera en cañas</b>", f"Vale {simbolo}{_num(c.valor)}"]
    if c.cuantas == 0:
        texto.append("No te da ni para una caña 😅")
    else:
        cuantas = _es(f"{c.cuantas:,}")
        texto.append(f"Te da para <b>{cuantas} caña{'s' if c.cuantas > 1 else ''}</b>")
    if c.rondas:
        rondas = "1 ronda" if c.rondas == 1 else f"{_es(f'{c.rondas:,}')} rondas"
        texto.append(f"Si invitas tú, {rondas} para cuatro")
    texto.append(f"<i>A unos {simbolo}{PRECIO_CANA} cada una</i>")
    return "\n".join(texto)


def formatear_cine(c: Cine, currency: str) -> str:
    """Respuesta de /cine."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🎬 <b>Tu cartera en cine</b>", f"Vale {simbolo}{_num(c.valor)}"]
    if c.entradas == 0:
        texto.append("No te da ni para una entrada 😅")
    else:
        cuantas = _es(f"{c.entradas:,}")
        plural = "s" if c.entradas > 1 else ""
        texto.append(f"Te da para <b>{cuantas} entrada{plural}</b>")
        if c.años >= 1:
            para = f"{c.años:.1f} años".replace(".", ",")
        else:
            para = "1 semana" if c.entradas == 1 else f"{c.entradas} semanas"
        texto.append(f"Una peli a la semana, tienes para {para}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_CINE} la entrada</i>")
    return "\n".join(texto)


def formatear_super(s: Super, currency: str) -> str:
    """Respuesta de /super."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🛒 <b>Tu cartera en carros de la compra</b>",
        f"Vale {simbolo}{_num(s.valor)}",
    ]
    if s.carros == 0:
        texto.append("No te da ni para un carro 😅")
    else:
        plural = "s" if s.carros > 1 else ""
        texto.append(f"Te da para <b>{_es(f'{s.carros:,}')} carro{plural}</b>")
        if s.años >= 1:
            # Sin esto, de 52 a 54 carros salía "1,0 años"
            años = f"{s.años:.1f}".replace(".", ",").removesuffix(",0")
            para = "1 año" if años == "1" else f"{años} años"
        else:
            para = "1 semana" if s.carros == 1 else f"{s.carros} semanas"
        texto.append(f"Uno a la semana, comes {para}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_SUPER} el carro</i>")
    return "\n".join(texto)


def formatear_kebab(k: Kebab, currency: str) -> str:
    """Respuesta de /kebab."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🥙 <b>Tu cartera en kebabs</b>", f"Vale {simbolo}{_num(k.valor)}"]
    if k.kebabs == 0:
        texto.append("No te da ni para un kebab 😅")
    else:
        plural = "s" if k.kebabs > 1 else ""
        texto.append(f"Te da para <b>{_es(f'{k.kebabs:,}')} kebab{plural}</b>")
        if k.años >= 1:
            años = f"{k.años:.1f}".replace(".", ",").removesuffix(",0")
            para = "1 año" if años == "1" else f"{años} años"
        else:
            para = f"{k.kebabs} viernes"
        texto.append(f"Uno cada viernes, cenas {para}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_KEBAB} el kebab</i>")
    return "\n".join(texto)


def formatear_churros(c: Churros, currency: str) -> str:
    """Respuesta de /churros."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🍫 <b>Tu cartera en chocolate con churros</b>",
        f"Vale {simbolo}{_num(c.valor)}",
    ]
    if c.raciones == 0:
        texto.append("No te da ni para un chocolate con churros 😅")
    else:
        cuantos = _es(f"{c.raciones:,}")
        plural = "s" if c.raciones > 1 else ""
        texto.append(f"Te da para <b>{cuantos} chocolate{plural} con churros</b>")
        if c.años >= 1:
            años = f"{c.años:.1f}".replace(".", ",").removesuffix(",0")
            para = "1 año" if años == "1" else f"{años} años"
        else:
            para = "1 semana" if c.raciones == 1 else f"{c.raciones} semanas"
        texto.append(f"Unos cada domingo, tienes para {para}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_CHURROS} la taza con media docena</i>")
    return "\n".join(texto)


def formatear_loteria(lo: Loteria, currency: str) -> str:
    """Respuesta de /loteria."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🎄 <b>Tu cartera en décimos de Navidad</b>",
        f"Vale {simbolo}{_num(lo.valor)}",
    ]
    if lo.decimos == 0:
        texto.append("No te da ni para un décimo 😅")
    else:
        plural = "s" if lo.decimos > 1 else ""
        texto.append(f"Te da para <b>{_es(f'{lo.decimos:,}')} décimo{plural}</b>")
    if lo.faltan == 0:
        texto.append("🎉 ¡El sorteo es hoy!")
    elif lo.faltan == 1:
        texto.append("Falta 1 día para el sorteo del 22 de diciembre")
    else:
        texto.append(f"Faltan {lo.faltan} días para el sorteo del 22 de diciembre")
    texto.append(f"<i>A {simbolo}{PRECIO_LOTERIA} el décimo</i>")
    return "\n".join(texto)


def formatear_piso(p: Piso, currency: str) -> str:
    """Respuesta de /piso."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🏠 <b>Tu cartera en metros de piso</b>", f"Vale {simbolo}{_num(p.valor)}"]
    # Por debajo de 0,1 m² saldría "0 m²", que queda raro.
    if p.metros < 0.1:
        texto.append("No llega ni a una baldosa 😅")
    else:
        metros = _es(f"{p.metros:,.1f}").removesuffix(",0")
        texto.append(f"Te da para <b>{metros} m²</b> en Madrid")
    if p.pisos == 0:
        falta = f"{simbolo}{_num(p.falta)}"
        texto.append(f"Para un piso de {METROS_PISO} m² te faltan {falta}")
    else:
        plural = "s" if p.pisos > 1 else ""
        pisos = _es(f"{p.pisos:,}")
        texto.append(f"Son <b>{pisos} piso{plural}</b> de {METROS_PISO} m²")
    precio = _es(f"{PRECIO_PISO:,}")
    texto.append(f"<i>A unos {simbolo}{precio} el m², en Madrid capital</i>")
    return "\n".join(texto)


def formatear_futbol(f: Futbol, currency: str) -> str:
    """Respuesta de /futbol."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "⚽ <b>Tu cartera en entradas de fútbol</b>",
        f"Vale {simbolo}{_num(f.valor)}",
    ]
    if f.entradas == 0:
        texto.append("No te da ni para una entrada 😅")
    else:
        plural = "s" if f.entradas > 1 else ""
        texto.append(f"Te da para <b>{_es(f'{f.entradas:,}')} entrada{plural}</b>")
        if f.temporadas >= 1:
            temporadas = f"{f.temporadas:.1f}".replace(".", ",").removesuffix(",0")
            para = "1 temporada" if temporadas == "1" else f"{temporadas} temporadas"
        else:
            para = "1 partido" if f.entradas == 1 else f"{f.entradas} partidos"
        texto.append(f"Yendo a todos los partidos en casa, tienes para {para}")
    texto.append(
        f"<i>A unos {simbolo}{PRECIO_FUTBOL} la entrada, en un partido de liga</i>"
    )
    return "\n".join(texto)


def formatear_taxi(t: Taxi, currency: str) -> str:
    """Respuesta de /taxi."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🚕 <b>Tu cartera en taxis al aeropuerto</b>",
        f"Vale {simbolo}{_num(t.valor)}",
    ]
    if t.viajes == 0:
        texto.append("No te da ni para un taxi 😅")
    else:
        plural = "s" if t.viajes > 1 else ""
        texto.append(f"Te da para <b>{_es(f'{t.viajes:,}')} viaje{plural}</b>")
        if t.escapadas == 0:
            texto.append("Solo la ida, la vuelta en metro")
        else:
            plural = "s" if t.escapadas > 1 else ""
            escapadas = _es(f"{t.escapadas:,}")
            texto.append(f"Contando ida y vuelta, son {escapadas} escapada{plural}")
    texto.append(
        f"<i>A {simbolo}{PRECIO_TAXI} el viaje, la tarifa fija de Madrid a Barajas</i>"
    )
    return "\n".join(texto)


def formatear_tortilla(t: Tortilla, currency: str) -> str:
    """Respuesta de /tortilla."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🥔 <b>Tu cartera en pinchos de tortilla</b>",
        f"Vale {simbolo}{_num(t.valor)}",
    ]
    if t.pinchos == 0:
        texto.append("No te da ni para un pincho 😅")
    else:
        plural = "s" if t.pinchos > 1 else ""
        texto.append(f"Te da para <b>{_es(f'{t.pinchos:,}')} pincho{plural}</b>")
        if t.años >= 1:
            años = f"{t.años:.1f}".replace(".", ",").removesuffix(",0")
            para = "1 año" if años == "1" else f"{años} años"
        else:
            para = "1 día" if t.pinchos == 1 else f"{t.pinchos} días"
        texto.append(f"Uno cada mañana con el café, tienes para {para}")
    texto.append(
        f"<i>A unos {simbolo}{PRECIO_TORTILLA} el pincho, en un bar de barrio</i>"
    )
    return "\n".join(texto)


def formatear_videojuego(v: Videojuego, currency: str) -> str:
    """Respuesta de /videojuego."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🎮 <b>Tu cartera en videojuegos</b>", f"Vale {simbolo}{_num(v.valor)}"]
    if v.juegos == 0:
        texto.append("No te da ni para un juego 😅")
    else:
        plural = "s" if v.juegos > 1 else ""
        texto.append(f"Te da para <b>{_es(f'{v.juegos:,}')} juego{plural}</b>")
        if v.años >= 1:
            años = f"{v.años:.1f}".replace(".", ",").removesuffix(",0")
            para = "1 año" if años == "1" else f"{años} años"
        else:
            para = "1 mes" if v.juegos == 1 else f"{v.juegos} meses"
        texto.append(f"Comprando uno al mes, tienes para {para}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_VIDEOJUEGO} el juego, recién salido</i>")
    return "\n".join(texto)


def formatear_carnet(c: Carnet, currency: str) -> str:
    """Respuesta de /carnet."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🚦 <b>Tu cartera en carnets de conducir</b>",
        f"Vale {simbolo}{_num(c.valor)}",
    ]
    if c.enteros == 0:
        texto.append(f"Te da para el <b>{c.parte:.0f}%</b> de uno")
        siguiente = "el primero"
    else:
        cuantos = _es(f"{c.enteros:,}")
        plural = "s" if c.enteros > 1 else ""
        texto.append(f"Te da para <b>{cuantos} carnet{plural}</b>")
        siguiente = "el siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(c.falta)}")
    texto.append(
        f"<i>A unos {simbolo}{PRECIO_CARNET} cada uno, aprobando a la primera</i>"
    )
    return "\n".join(texto)


def formatear_boda(b: Boda, currency: str) -> str:
    """Respuesta de /boda."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["💍 <b>Tu cartera en bodas</b>", f"Vale {simbolo}{_num(b.valor)}"]
    if b.enteros == 0:
        texto.append(f"Te da para el <b>{b.parte:.0f}%</b> de una")
        siguiente = "la primera"
    else:
        cuantas = _es(f"{b.enteros:,}")
        plural = "s" if b.enteros > 1 else ""
        texto.append(f"Te da para <b>{cuantas} boda{plural}</b>")
        siguiente = "la siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(b.falta)}")
    precio = _es(f"{PRECIO_BODA:,}")
    texto.append(f"<i>A unos {simbolo}{precio} cada una, con cien invitados</i>")
    return "\n".join(texto)


def formatear_jamon(j: Jamon, currency: str) -> str:
    """Respuesta de /jamon."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🍖 <b>Tu cartera en jamones</b>", f"Vale {simbolo}{_num(j.valor)}"]
    if j.enteros == 0:
        texto.append(f"Te da para el <b>{j.parte:.0f}%</b> de uno")
        siguiente = "el primero"
    else:
        cuantos = _es(f"{j.enteros:,}")
        texto.append(
            f"Te da para <b>{cuantos} {'jamones' if j.enteros > 1 else 'jamón'}</b>"
        )
        siguiente = "el siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(j.falta)}")
    texto.append(
        f"<i>A unos {simbolo}{PRECIO_JAMON} la pata de bellota 100% ibérica</i>"
    )
    return "\n".join(texto)


def formatear_emoji(cambio: float) -> str:
    """Respuesta de /emoji: la cara grande y debajo el porqué."""
    emoji, frase = cara_emoji(cambio)
    return f"{emoji}\n\n<b>{frase}</b>\nTu cartera va <b>{cambio:+.2f}%</b> en 24 h"


def formatear_tiempo(cambio: float) -> str:
    """Respuesta de /tiempo."""
    emoji, cielo, consejo = parte_tiempo(cambio)
    return (
        f"{emoji} <b>{cielo}</b>\n"
        f"Tu cartera va <b>{cambio:+.2f}%</b> en 24 h\n"
        f"<i>{consejo}</i>"
    )


def formatear_rolex(r: Rolex, currency: str) -> str:
    """Respuesta de /rolex."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["⌚ <b>Tu cartera en Rolex</b>", f"Vale {simbolo}{_num(r.valor)}"]
    if r.enteros == 0:
        texto.append(f"Te da para el <b>{r.parte:.0f}%</b> de uno")
        siguiente = "el primero"
    else:
        # Rolex no cambia en plural
        texto.append(f"Te da para <b>{_es(f'{r.enteros:,}')} Rolex</b>")
        siguiente = "el siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(r.falta)}")
    precio = _es(f"{PRECIO_ROLEX:,}")
    texto.append(f"<i>A unos {simbolo}{precio} un Submariner nuevo</i>")
    return "\n".join(texto)


def formatear_aceite(a: Aceite, currency: str) -> str:
    """Respuesta de /aceite."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🫒 <b>Tu cartera en aceite de oliva</b>",
        f"Vale {simbolo}{_num(a.valor)}",
    ]
    if a.enteros == 0:
        texto.append(f"Te da para el <b>{a.parte:.0f}%</b> de uno")
        siguiente = "el primero"
    else:
        cuantos = _es(f"{a.enteros:,}")
        texto.append(
            f"Te da para <b>{cuantos} {'litros' if a.enteros > 1 else 'litro'}</b>"
        )
        siguiente = "el siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(a.falta)}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_ACEITE} el litro de virgen extra</i>")
    return "\n".join(texto)


def formatear_paella(p: Paella, currency: str) -> str:
    """Respuesta de /paella."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🥘 <b>Tu cartera en paellas</b>", f"Vale {simbolo}{_num(p.valor)}"]
    if p.enteros == 0:
        texto.append(f"Te da para el <b>{p.parte:.0f}%</b> de una")
        siguiente = "la primera"
    else:
        cuantos = _es(f"{p.enteros:,}")
        texto.append(
            f"Te da para <b>{cuantos} {'paellas' if p.enteros > 1 else 'paella'}</b>"
        )
        siguiente = "la siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(p.falta)}")
    texto.append(
        f"<i>A unos {simbolo}{PRECIO_PAELLA} la de cuatro en un restaurante</i>"
    )
    return "\n".join(texto)


def formatear_croquetas(c: Croquetas, currency: str) -> str:
    """Respuesta de /croquetas."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🧆 <b>Tu cartera en croquetas</b>", f"Vale {simbolo}{_num(c.valor)}"]
    if c.enteros == 0:
        texto.append(f"Te da para el <b>{c.parte:.0f}%</b> de una")
        siguiente = "la primera"
    else:
        cuantos = _es(f"{c.enteros:,}")
        texto.append(
            f"Te da para <b>{cuantos} {'raciones' if c.enteros > 1 else 'ración'}</b>"
        )
        siguiente = "la siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(c.falta)}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_CROQUETAS} la ración de ocho caseras</i>")
    return "\n".join(texto)


def formatear_pan(p: Pan, currency: str) -> str:
    """Respuesta de /pan."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🥖 <b>Tu cartera en barras de pan</b>", f"Vale {simbolo}{_num(p.valor)}"]
    if p.enteros == 0:
        texto.append(f"Te da para el <b>{p.parte:.0f}%</b> de una")
        siguiente = "la primera"
    else:
        cuantos = _es(f"{p.enteros:,}")
        texto.append(
            f"Te da para <b>{cuantos} {'barras' if p.enteros > 1 else 'barra'}</b>"
        )
        siguiente = "la siguiente"
    # Siempre con dos decimales: _num pone cuatro por debajo de 1 y aquí casi siempre
    # falta menos de un euro.
    falta = _es(f"{p.falta:,.2f}")
    texto.append(f"Para {siguiente} te faltan {simbolo}{falta}")
    texto.append(f"<i>A unos {simbolo}{_num(PRECIO_PAN)} la barra en la panadería</i>")
    return "\n".join(texto)


def formatear_coche(c: Coche, currency: str) -> str:
    """Respuesta de /coche."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🚗 <b>Tu cartera en coches</b>", f"Vale {simbolo}{_num(c.valor)}"]
    if c.enteros == 0:
        texto.append(f"Te da para el <b>{c.parte:.0f}%</b> de uno")
        siguiente = "el primero"
    else:
        cuantos = _es(f"{c.enteros:,}")
        plural = "s" if c.enteros > 1 else ""
        texto.append(f"Te da para <b>{cuantos} coche{plural}</b>")
        siguiente = "el siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(c.falta)}")
    precio = _es(f"{PRECIO_COCHE:,}")
    texto.append(f"<i>A unos {simbolo}{precio} cada uno, un utilitario nuevo</i>")
    return "\n".join(texto)


def formatear_sofa(s: Sofa, currency: str) -> str:
    """Respuesta de /sofa."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🛋️ <b>Tu cartera en sofás</b>", f"Vale {simbolo}{_num(s.valor)}"]
    if s.enteros == 0:
        texto.append(f"Te da para el <b>{s.parte:.0f}%</b> de uno")
        siguiente = "el primero"
    else:
        cuantos = _es(f"{s.enteros:,}")
        plural = "s" if s.enteros > 1 else ""
        texto.append(f"Te da para <b>{cuantos} sofá{plural}</b>")
        siguiente = "el siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(s.falta)}")
    texto.append(
        f"<i>A unos {simbolo}{PRECIO_SOFA} cada uno, de tres plazas de IKEA</i>"
    )
    return "\n".join(texto)


def formatear_navidad(n: Navidad, currency: str) -> str:
    """Respuesta de /navidad."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    if n.faltan == 0:
        titulo = "🎄 <b>¡Feliz Navidad!</b>"
    elif n.faltan == 1:
        titulo = "🎅 <b>Mañana es Navidad</b>"
    else:
        titulo = f"🎅 <b>Faltan {n.faltan} días para Navidad</b>"
    texto = [titulo, f"Tu cartera vale {simbolo}{_num(n.valor)}"]
    if n.cestas == 0:
        texto.append("No te da ni para una cesta 😅")
    elif n.cestas == 1:
        texto.append("Te da para <b>1 cesta navideña</b>")
    else:
        texto.append(f"Te da para <b>{_es(f'{n.cestas:,}')} cestas navideñas</b>")
    texto.append(
        f"<i>A unos {simbolo}{PRECIO_NAVIDAD} la cesta, con turrón, embutido y cava</i>"
    )
    return "\n".join(texto)


def formatear_nochevieja(n: Nochevieja, currency: str) -> str:
    """Respuesta de /nochevieja."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    if n.faltan == 0:
        titulo = "🎉 <b>¡Hoy es Nochevieja!</b>"
    elif n.faltan == 1:
        titulo = "🍇 <b>Mañana es Nochevieja</b>"
    else:
        titulo = f"🥂 <b>Faltan {n.faltan} días para Nochevieja</b>"
    llenas = round(n.pasado / 10)
    texto = [
        titulo,
        f"{'▰' * llenas}{'▱' * (10 - llenas)} llevas el {n.pasado:.0f}% del año",
        f"Tu cartera vale {simbolo}{_num(n.valor)}",
    ]
    if n.botellas == 0:
        texto.append("No te da ni para una botella 😅")
    elif n.botellas == 1:
        texto.append("Te da para <b>1 botella de cava</b>")
    else:
        texto.append(f"Te da para <b>{_es(f'{n.botellas:,}')} botellas de cava</b>")
    texto.append(f"<i>A unos {simbolo}{PRECIO_CAVA} la botella, de supermercado</i>")
    return "\n".join(texto)


def formatear_iphone(i: Iphone, currency: str) -> str:
    """Respuesta de /iphone."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["📱 <b>Tu cartera en iPhones</b>", f"Vale {simbolo}{_num(i.valor)}"]
    if i.enteros == 0:
        texto.append(f"Te da para el <b>{i.parte:.0f}%</b> de uno")
        siguiente = "el primero"
    else:
        cuantos = f"{i.enteros:,}".replace(",", ".") + " iPhone"
        texto.append(f"Te da para <b>{cuantos}{'s' if i.enteros > 1 else ''}</b>")
        siguiente = "el siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(i.falta)}")
    precio = f"{PRECIO_IPHONE:,}".replace(",", ".")
    texto.append(f"<i>A unos {simbolo}{precio} cada uno, el Pro</i>")
    return "\n".join(texto)


def formatear_macbook(m: Macbook, currency: str) -> str:
    """Respuesta de /macbook."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["💻 <b>Tu cartera en MacBooks</b>", f"Vale {simbolo}{_num(m.valor)}"]
    if m.enteros == 0:
        texto.append(f"Te da para el <b>{m.parte:.0f}%</b> de uno")
        siguiente = "el primero"
    else:
        texto.append(f"Te da para <b>{_es(f'{m.enteros:,}')} MacBook Air</b>")
        siguiente = "el siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(m.falta)}")
    precio = _es(f"{PRECIO_MACBOOK:,}")
    texto.append(f'<i>A unos {simbolo}{precio} cada uno, el Air de 13"</i>')
    return "\n".join(texto)


def formatear_bici(b: Bici, currency: str) -> str:
    """Respuesta de /bici."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🚴 <b>Tu cartera en bicis</b>", f"Vale {simbolo}{_num(b.valor)}"]
    if b.enteras == 0:
        texto.append(f"Te da para el <b>{b.parte:.0f}%</b> de una")
        siguiente = "la primera"
    else:
        cuantas = _es(f"{b.enteras:,}")
        plural = "s" if b.enteras > 1 else ""
        texto.append(f"Te da para <b>{cuantas} bici{plural} de carretera</b>")
        siguiente = "la siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(b.falta)}")
    texto.append(
        f"<i>A unos {simbolo}{PRECIO_BICI} cada una, de aluminio para empezar</i>"
    )
    return "\n".join(texto)


def formatear_alquiler(a: Alquiler, currency: str) -> str:
    """Respuesta de /alquiler."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🏠 <b>Tu cartera en meses de alquiler</b>",
        f"Vale {simbolo}{_num(a.valor)}",
    ]
    if a.meses == 0:
        dias = "1 día" if a.dias == 1 else f"{a.dias} días"
        texto.append(f"No llega a un mes: te paga <b>{dias}</b>")
    else:
        texto.append(f"Te paga {_meses(a.meses)}")
    precio = f"{PRECIO_ALQUILER:,}".replace(",", ".")
    texto.append(f"<i>A unos {simbolo}{precio} al mes, un piso normal en España</i>")
    return "\n".join(texto)


def formatear_netflix(n: Netflix, currency: str) -> str:
    """Respuesta de /netflix."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🍿 <b>Tu cartera en Netflix</b>", f"Vale {simbolo}{_num(n.valor)}"]
    if n.meses == 0:
        texto.append("No te paga ni un mes 😅")
    else:
        texto.append(f"Te paga {_meses(n.meses)}")
    texto.append(f"<i>A {simbolo}{_num(PRECIO_NETFLIX)} al mes, el plan Estándar</i>")
    return "\n".join(texto)


def formatear_spotify(s: Spotify, currency: str) -> str:
    """Respuesta de /spotify."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🎧 <b>Tu cartera en Spotify</b>", f"Vale {simbolo}{_num(s.valor)}"]
    if s.meses == 0:
        texto.append("No te paga ni un mes 😅")
    else:
        texto.append(f"Te paga {_meses(s.meses)}")
    precio = _num(PRECIO_SPOTIFY)
    texto.append(f"<i>A {simbolo}{precio} al mes, el Premium Individual</i>")
    return "\n".join(texto)


def formatear_gimnasio(g: Gimnasio, currency: str) -> str:
    """Respuesta de /gimnasio."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🏋️ <b>Tu cartera en gimnasio</b>", f"Vale {simbolo}{_num(g.valor)}"]
    if g.meses == 0:
        texto.append("No te paga ni un mes 😅")
    else:
        texto.append(f"Te paga {_meses(g.meses)}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_GIMNASIO} al mes</i>")
    return "\n".join(texto)


def formatear_metro(m: Metro, currency: str) -> str:
    """Respuesta de /metro."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🚇 <b>Tu cartera en abonos de transporte</b>",
        f"Vale {simbolo}{_num(m.valor)}",
    ]
    if m.meses == 0:
        texto.append("No te paga ni un mes 😅")
    else:
        texto.append(f"Te paga {_meses(m.meses)}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_METRO} el abono mensual</i>")
    return "\n".join(texto)


def formatear_luz(luz: Luz, currency: str) -> str:
    """Respuesta de /luz."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "💡 <b>Tu cartera en facturas de la luz</b>",
        f"Vale {simbolo}{_num(luz.valor)}",
    ]
    if luz.meses == 0:
        texto.append("No te paga ni un mes 😅")
    else:
        texto.append(f"Te paga {_meses(luz.meses)}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_LUZ} la factura del mes</i>")
    return "\n".join(texto)


def formatear_libro(li: Libro, currency: str) -> str:
    """Respuesta de /libro."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["📚 <b>Tu cartera en libros</b>", f"Vale {simbolo}{_num(li.valor)}"]
    if li.libros == 0:
        texto.append("No te da ni para un libro 😅")
    else:
        plural = "s" if li.libros > 1 else ""
        texto.append(f"Te da para <b>{_es(f'{li.libros:,}')} libro{plural}</b>")
        años, resto = divmod(li.libros, 12)
        if años:
            para = "1 año" if años == 1 else f"{_es(f'{años:,}')} años"
            if resto:
                para += " y pico"
        else:
            para = "1 mes" if resto == 1 else f"{resto} meses"
        texto.append(f"Leyendo uno al mes, tienes para {para}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_LIBRO} el libro</i>")
    return "\n".join(texto)


def formatear_concierto(c: Concierto, currency: str) -> str:
    """Respuesta de /concierto."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🎤 <b>Tu cartera en conciertos</b>", f"Vale {simbolo}{_num(c.valor)}"]
    if c.entradas == 0:
        texto.append("No te da ni para una entrada 😅")
    else:
        plural = "s" if c.entradas > 1 else ""
        texto.append(f"Te da para <b>{_es(f'{c.entradas:,}')} entrada{plural}</b>")
        if c.para_dos:
            cuantos = _es(f"{c.para_dos:,}")
            plural = "s" if c.para_dos > 1 else ""
            texto.append(f"Si invitas tú, {cuantos} concierto{plural} para dos")
    texto.append(f"<i>A unos {simbolo}{PRECIO_CONCIERTO} la entrada</i>")
    return "\n".join(texto)


def _meses(meses: int) -> str:
    """<b>30 meses</b>, más de 2 años"""
    texto = "<b>1 mes</b>" if meses == 1 else f"<b>{_es(f'{meses:,}')} meses</b>"
    años = meses // 12
    if años:
        cuantos = "1 año" if años == 1 else f"{_es(f'{años:,}')} años"
        texto += f", {'justo' if meses % 12 == 0 else 'más de'} {cuantos}"
    return texto


def formatear_oro(o: Oro, currency: str) -> str:
    """Respuesta de /oro."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    if o.gramos >= 1000:
        peso = _es(f"{o.gramos / 1000:,.1f}".removesuffix(".0")) + " kilos"
    elif o.gramos >= 10:
        peso = f"{o.gramos:.0f} gramos"
    else:
        peso = _es(f"{o.gramos:.1f}".removesuffix(".0")) + " gramos"
    onzas = _es(f"{o.onzas:,.2f}")
    return "\n".join(
        [
            "🥇 <b>Tu cartera en oro</b>",
            f"Vale {simbolo}{_num(o.valor)}",
            f"Son <b>{peso}</b>, {onzas} onzas",
            f"<i>Con el gramo a {simbolo}{_num(o.gramo)}</i>",
        ]
    )


def _es(numero: str) -> str:
    """1,234.5 → 1.234,5"""
    return numero.replace(",", " ").replace(".", ",").replace(" ", ".")


def formatear_ps5(p: Ps5, currency: str) -> str:
    """Respuesta de /ps5."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🎮 <b>Tu cartera en PS5</b>", f"Vale {simbolo}{_num(p.valor)}"]
    if p.enteros == 0:
        texto.append(f"Te da para el <b>{p.parte:.0f}%</b> de una")
        siguiente = "la primera"
    else:
        texto.append(f"Te da para <b>{_es(f'{p.enteros:,}')} PS5</b>")
        siguiente = "la siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(p.falta)}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_PS5} cada una, la Pro</i>")
    return "\n".join(texto)


def formatear_switch(s: Switch, currency: str) -> str:
    """Respuesta de /switch."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🕹️ <b>Tu cartera en Switch 2</b>", f"Vale {simbolo}{_num(s.valor)}"]
    if s.enteros == 0:
        texto.append(f"Te da para el <b>{s.parte:.0f}%</b> de una")
        siguiente = "la primera"
    else:
        texto.append(f"Te da para <b>{_es(f'{s.enteros:,}')} Switch 2</b>")
        siguiente = "la siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(s.falta)}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_SWITCH} cada una, sin juego</i>")
    return "\n".join(texto)


def formatear_airpods(a: Airpods, currency: str) -> str:
    """Respuesta de /airpods."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🎧 <b>Tu cartera en AirPods Pro</b>", f"Vale {simbolo}{_num(a.valor)}"]
    if a.enteros == 0:
        texto.append(f"Te da para el <b>{a.parte:.0f}%</b> de unos")
        siguiente = "los primeros"
    else:
        texto.append(f"Te da para <b>{_es(f'{a.enteros:,}')} AirPods Pro</b>")
        siguiente = "los siguientes"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(a.falta)}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_AIRPODS} cada uno</i>")
    return "\n".join(texto)


def formatear_zapatillas(z: Zapatillas, currency: str) -> str:
    """Respuesta de /zapatillas."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["👟 <b>Tu cartera en zapatillas</b>", f"Vale {simbolo}{_num(z.valor)}"]
    if z.pares == 0:
        texto.append("No te da ni para un par 😅")
    else:
        cuantos = "1 par" if z.pares == 1 else f"{_es(f'{z.pares:,}')} pares"
        texto.append(f"Te da para <b>{cuantos}</b>")
        # Con menos de un año queda raro, se ve ya con los pares
        if z.años:
            años = "1 año" if z.años == 1 else f"{_es(f'{z.años:,}')} años"
            texto.append(f"Estrenando unas cada temporada, vas calzado {años}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_ZAPATILLAS} el par</i>")
    return "\n".join(texto)


def formatear_ave(a: Ave, currency: str) -> str:
    """Respuesta de /ave."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🚄 <b>Tu cartera en AVE a Barcelona</b>",
        f"Vale {simbolo}{_num(a.valor)}",
    ]
    if a.viajes == 0:
        texto.append("No te da ni para un viaje 😅")
    else:
        plural = "s" if a.viajes > 1 else ""
        texto.append(f"Te da para <b>{_es(f'{a.viajes:,}')} viaje{plural}</b>")
        años, resto = divmod(a.viajes, 12)
        if años:
            para = "1 año" if años == 1 else f"{_es(f'{años:,}')} años"
            if resto:
                para += " y pico"
        else:
            para = "1 mes" if resto == 1 else f"{resto} meses"
        texto.append(f"Un finde al mes, tienes escapadas para {para}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_AVE} ida y vuelta, desde Madrid</i>")
    return "\n".join(texto)


def formatear_menu(m: Menu, currency: str) -> str:
    """Respuesta de /menu."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🍽 <b>Tu cartera en menús del día</b>",
        f"Vale {simbolo}{_num(m.valor)}",
    ]
    if m.menus == 0:
        texto.append("No te da ni para un menú 😅")
    else:
        plural = "s" if m.menus > 1 else ""
        texto.append(f"Te da para <b>{_es(f'{m.menus:,}')} menú{plural}</b>")
        if m.años >= 1:
            años = f"{m.años:.1f}".replace(".", ",").removesuffix(",0")
            para = "1 año" if años == "1" else f"{años} años"
        elif m.semanas:
            para = "1 semana" if m.semanas == 1 else f"{m.semanas} semanas"
        else:
            para = "1 día" if m.menus == 1 else f"{m.menus} días"
        texto.append(f"De lunes a viernes, comes fuera {para}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_MENU} el menú, con bebida y postre</i>")
    return "\n".join(texto)


def formatear_hotel(h: Hotel, currency: str) -> str:
    """Respuesta de /hotel."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🏨 <b>Tu cartera en noches de hotel</b>",
        f"Vale {simbolo}{_num(h.valor)}",
    ]
    if h.noches == 0:
        texto.append("No te da ni para una noche 😅")
    else:
        plural = "s" if h.noches > 1 else ""
        texto.append(f"Te da para <b>{_es(f'{h.noches:,}')} noche{plural}</b>")
        if h.findes == 0:
            texto.append("Para un finde entero te falta otra")
        elif h.findes == 1:
            texto.append("Es 1 escapada de finde, de viernes a domingo")
        else:
            cuantas = _es(f"{h.findes:,}")
            texto.append(f"Son {cuantas} escapadas de finde, de viernes a domingo")
    texto.append(f"<i>A unos {simbolo}{PRECIO_HOTEL} la noche, en habitación doble</i>")
    return "\n".join(texto)


def formatear_peluqueria(p: Peluqueria, currency: str) -> str:
    """Respuesta de /peluqueria."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "💈 <b>Tu cartera en cortes de pelo</b>",
        f"Vale {simbolo}{_num(p.valor)}",
    ]
    if p.cortes == 0:
        texto.append("No te da ni para un corte 😅")
    else:
        plural = "s" if p.cortes > 1 else ""
        texto.append(f"Te da para <b>{_es(f'{p.cortes:,}')} corte{plural}</b>")
        años, resto = divmod(p.cortes, 12)
        if años:
            para = "<b>1 año</b>" if años == 1 else f"<b>{_es(f'{años:,}')} años</b>"
            if resto:
                para += " y pico"
        else:
            para = "<b>1 mes</b>" if resto == 1 else f"<b>{resto} meses</b>"
        texto.append(f"Uno al mes, vas bien peinado {para}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_PELUQUERIA} el corte</i>")
    return "\n".join(texto)


def formatear_tesla(t: Tesla, currency: str) -> str:
    """Respuesta de /tesla."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🚗 <b>Tu cartera en Teslas</b>", f"Vale {simbolo}{_num(t.valor)}"]
    if t.enteros == 0:
        texto.append(f"Te da para el <b>{t.parte:.0f}%</b> de uno")
        siguiente = "el primero"
    else:
        cuantos = f"{_es(f'{t.enteros:,}')} Tesla{'s' if t.enteros > 1 else ''}"
        texto.append(f"Te da para <b>{cuantos}</b>")
        siguiente = "el siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(t.falta)}")
    precio = _es(f"{PRECIO_TESLA:,}")
    texto.append(f"<i>A unos {simbolo}{precio} cada uno, el Model 3</i>")
    return "\n".join(texto)


def formatear_vuelo(v: Vuelo, currency: str) -> str:
    """Respuesta de /vuelo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "✈️ <b>Tu cartera en vuelos a Nueva York</b>",
        f"Vale {simbolo}{_num(v.valor)}",
    ]
    if v.enteros == 0:
        texto.append(f"Te da para el <b>{v.parte:.0f}%</b> de uno")
        siguiente = "el primero"
    else:
        cuantos = f"{_es(f'{v.enteros:,}')} viaje{'s' if v.enteros > 1 else ''}"
        texto.append(f"Te da para <b>{cuantos}</b>")
        siguiente = "el siguiente"
    texto.append(f"Para {siguiente} te faltan {simbolo}{_num(v.falta)}")
    texto.append(f"<i>A unos {simbolo}{PRECIO_VUELO} ida y vuelta, desde Madrid</i>")
    return "\n".join(texto)


def formatear_bigmac(b: BigMac, currency: str) -> str:
    """Respuesta de /bigmac."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🍔 <b>Tu cartera en Big Macs</b>", f"Vale {simbolo}{_num(b.valor)}"]
    if b.cuantos == 0:
        texto.append("No te da ni para un Big Mac 😅")
    else:
        cuantos = f"{b.cuantos:,}".replace(",", ".") + " Big Mac"
        texto.append(f"Te da para <b>{cuantos}{'s' if b.cuantos > 1 else ''}</b>")
    texto.append(f"<i>A unos {simbolo}{_num(PRECIO_BIGMAC)} cada uno</i>")
    return "\n".join(texto)


def formatear_gasolina(g: Gasolina, currency: str) -> str:
    """Respuesta de /gasolina."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["⛽ <b>Tu cartera en gasolina</b>", f"Vale {simbolo}{_num(g.valor)}"]
    if g.litros == 0:
        texto.append("No te da ni para un litro 😅")
    else:
        litros = f"{g.litros:,}".replace(",", ".")
        texto.append(f"Te da para <b>{litros} litro{'s' if g.litros > 1 else ''}</b>")
        if g.depositos:
            depositos = f"{g.depositos:,}".replace(",", ".")
            texto.append(
                f"Son {depositos} depósito{'s' if g.depositos > 1 else ''} "
                f"de {DEPOSITO} litros"
            )
    texto.append(f"<i>A unos {simbolo}{_num(PRECIO_GASOLINA)} el litro</i>")
    return "\n".join(texto)


def formatear_sueldo(s: Sueldo) -> str:
    """Respuesta de /sueldo."""
    texto = ["💼 <b>Tu cartera en sueldos</b>", f"Vale €{_num(s.valor)}"]
    if s.meses < 1:
        texto.append("No llega ni a un mes de salario mínimo 😅")
    else:
        cuanto, unidad = (s.meses, "mes") if s.meses < 12 else (s.meses / 12, "año")
        cifra = f"{cuanto:.1f}".replace(".", ",")
        if cifra != "1,0":
            unidad += "es" if unidad == "mes" else "s"
        texto.append(f"Son <b>{cifra} {unidad}</b> de salario mínimo")
    texto.append(f"<i>El SMI de 2026: €{PAGA_SMI:,} en 14 pagas</i>".replace(",", "."))
    return "\n".join(texto)


def formatear_frase(f: Frase) -> str:
    """Respuesta de /frase."""
    quien = f"{f.autor}, {f.año}" if f.año else f.autor
    return f"💬 <i>«{escape(f.texto)}»</i>\n— {escape(quien)}"


def formatear_version(v: Version) -> str:
    """Respuesta de /version."""
    if v.numero is None:
        return "🏷️ <b>CryptoPriceTracker</b>\nNo he encontrado el número de versión."
    texto = [f"🏷️ <b>CryptoPriceTracker {escape(v.numero)}</b>"]
    if v.commit and v.fecha:
        año, mes, dia = v.fecha.split("-")
        texto.append(f"Último cambio: {v.commit}, del {dia}/{mes}/{año}")
    return "\n".join(texto)


def formatear_chiste(chiste: str) -> str:
    """Respuesta de /chiste."""
    return f"😂 {escape(chiste)}"


def formatear_consejo(consejo: str) -> str:
    """Respuesta de /consejo."""
    return (
        "🧠 <b>Consejo de inversión</b>\n"
        f"<i>«{escape(consejo)}»</i>\n"
        "<i>Es de broma, no le hagas caso</i>"
    )


def formatear_refran(refran: str) -> str:
    """Respuesta de /refran."""
    return (
        "📜 <b>Refranero cripto</b>\n"
        f"<i>«{escape(refran)}»</i>\n"
        "<i>Como decía mi abuela, que no tenía ni un bitcoin</i>"
    )


def formatear_excusa(excusa: str) -> str:
    """Respuesta de /excusa."""
    return (
        "🤷 <b>Excusa para hoy</b>\n"
        f"<i>«{escape(excusa)}»</i>\n"
        "<i>Cópiala y pégala en el grupo, que nadie pregunte más</i>"
    )


def formatear_bola(pregunta: str, respuesta: str) -> str:
    """Respuesta de /bola."""
    return (
        f"🎱 <b>{escape(pregunta)}</b>\n"
        f"<i>«{escape(respuesta)}»</i>\n"
        "<i>Es de broma: no le hagas caso a una bola</i>"
    )


def formatear_galleta(g: Galleta) -> str:
    """Respuesta de /galleta."""
    numeros = " · ".join(str(n) for n in g.numeros)
    return (
        "🥠 <b>Tu galleta de la suerte</b>\n"
        f"<i>«{escape(g.frase)}»</i>\n\n"
        f"Números de la suerte: <b>{numeros}</b>\n"
        "<i>Hasta mañana no te toca otra</i>"
    )


def formatear_tarot(c: Carta) -> str:
    """Respuesta de /tarot."""
    return (
        "🃏 <b>Tu carta del tarot cripto</b>\n\n"
        f"{c.emoji} <b>{escape(c.nombre)}</b>\n"
        f"<i>«{escape(c.significado)}»</i>\n"
        "<i>Es de broma: las cartas no saben de criptos</i>"
    )


def formatear_horoscopo(h: Horoscopo) -> str:
    """Respuesta de /horoscopo."""
    return (
        f"🔮 <b>{h.signo}</b>\n"
        f"<i>«{escape(h.prediccion)}»</i>\n\n"
        f"Cripto de la suerte: <b>{h.cripto}</b>\n"
        f"Número de la suerte: <b>{h.numero}</b>\n"
        "<i>Es de broma: los astros no saben de criptos</i>"
    )


def formatear_glosario(argumento: str) -> str:
    """Respuesta de /glosario: la lista a secas, o lo que significa una palabra."""
    if not argumento.strip():
        return (
            "📖 <b>Las palabras que sé</b>\n"
            + ", ".join(TERMINOS)
            + "\n<i>Pide una: /glosario hodl</i>"
        )
    termino = buscar(argumento)
    if termino:
        return f"📖 <b>{termino}</b>\n{TERMINOS[termino]}"
    pedido = escape(argumento.strip())
    cerca = parecido(argumento)
    if cerca:
        return f"No sé qué es «{pedido}». ¿Querías decir /glosario {cerca}?"
    return f"No sé qué es «{pedido}». Con /glosario te salen las que sé."


def formatear_caraocruz(lado: str, coin_id: str | None) -> str:
    """Respuesta de /caraocruz."""
    texto = f"🪙 Ha salido <b>{lado}</b>: {QUE_HACER[lado]}"
    if coin_id:
        texto += f" <b>{escape(coin_id.replace('-', ' ').title())}</b>"
    return texto + "\n<i>Es una moneda al aire. No es un consejo, que lo sepas.</i>"


def formatear_ppt(tuya: str, del_bot: str, como: str) -> str:
    """Respuesta de /ppt. como es ganas, pierdes o empate."""
    return (
        f"Tú {EMOJIS_PPT[tuya]} {tuya} · yo {EMOJIS_PPT[del_bot]} {del_bot}\n"
        f"<b>{QUE_HACER_PPT[como]}</b>\n"
        "<i>Es piedra, papel o tijera. No es un consejo, que lo sepas.</i>"
    )


def formatear_adivina(i: Intento, currency: str) -> str:
    """Respuesta de /adivina."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(i.coin_id.replace("-", " ").title())
    emoji, nota = i.nota
    texto = [
        f"{emoji} <b>{nota}</b>",
        f"Dijiste {simbolo}{_num(i.dicho)} y <b>{nombre}</b> está a "
        f"<b>{simbolo}{_num(i.precio)}</b>",
    ]
    if i.dicho != i.precio:
        lado = "corto" if i.corto else "pasado"
        texto.append(
            f"Te has quedado {lado} por {simbolo}{_num(abs(i.precio - i.dicho))} "
            f"({i.error:.2f}%)"
        )
    return "\n".join(texto)


def formatear_dado(numero: int, coin_id: str | None) -> str:
    """Respuesta de /dado."""
    que, enlace = QUE_HACER_DADO[numero - 1]
    texto = f"🎲 Ha salido un <b>{numero}</b> {CARAS[numero - 1]}: {que}"
    if coin_id:
        nombre = escape(coin_id.replace("-", " ").title())
        texto += f" {enlace} <b>{nombre}</b>".replace("  ", " ")
    return texto + "\n<i>Lo ha dicho un dado. No es un consejo, que lo sepas.</i>"


def formatear_sat(s: Sat, currency: str) -> str:
    """Respuesta de /sat."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [f"⚡ <b>1 sat vale {simbolo}{_num(s.valor)}</b>", ""]
    for dinero in CANTIDADES_SAT:
        sats = f"{s.por(dinero):,}".replace(",", ".")
        texto.append(f"{simbolo}{dinero} → {sats} sats")
    texto.append(
        f"\n<i>Un bitcoin son 100 millones de sats, a {simbolo}{_num(s.bitcoin)}</i>"
    )
    return "\n".join(texto)


def formatear_cumple(c: Cumple) -> str:
    """Respuesta de /cumple."""
    dias = f"{c.dias:,}".replace(",", ".")
    texto = (
        f"🎂 <b>Bitcoin tiene {c.años} años</b>\n"
        f"Nació el 03/01/2009 y lleva {dias} días funcionando"
    )
    if c.faltan == 0:
        return texto + "\n🎉 ¡Hoy es su cumpleaños!"
    falta = "1 día" if c.faltan == 1 else f"{c.faltan} días"
    return texto + f"\n<i>Faltan {falta} para que cumpla {c.años + 1}</i>"


def formatear_whitepaper(w: Whitepaper) -> str:
    """Respuesta de /whitepaper."""
    dias = f"{w.dias:,}".replace(",", ".")
    texto = (
        f"📄 <b>El whitepaper de Bitcoin tiene {w.años} años</b>\n"
        f"Satoshi lo publicó el 31/10/2008, hace {dias} días. Son 9 páginas"
    )
    if w.faltan == 0:
        return texto + "\n🎉 ¡Hoy es su cumpleaños!"
    falta = "1 día" if w.faltan == 1 else f"{w.faltan} días"
    return texto + f"\n<i>Faltan {falta} para que cumpla {w.años + 1}</i>"


def formatear_merge(m: Merge) -> str:
    """Respuesta de /merge."""
    dias = f"{m.dias:,}".replace(",", ".")
    años = "1 año" if m.años == 1 else f"{m.años} años"
    texto = (
        f"🐼 <b>The Merge cumple {años}</b>\n"
        f"Ethereum dejó la minería el 15/09/2022, hace {dias} días. "
        "Desde entonces gasta un 99,95 % menos de energía"
    )
    if m.faltan == 0:
        return texto + "\n🎉 ¡Hoy es su aniversario!"
    falta = "1 día" if m.faltan == 1 else f"{m.faltan} días"
    return texto + f"\n<i>Faltan {falta} para que cumpla {m.años + 1}</i>"


def formatear_ethereum(e: Ethereum) -> str:
    """Respuesta de /ethereum."""
    dias = _es(f"{e.dias:,}")
    años = "1 año" if e.años == 1 else f"{e.años} años"
    texto = (
        f"⟠ <b>Ethereum cumple {años}</b>\n"
        f"Arrancó el 30/07/2015, hace {dias} días. "
        "En la preventa de 2014 el ether salía a unos 0,31 $"
    )
    if e.faltan == 0:
        return texto + "\n🎉 ¡Hoy es su cumpleaños!"
    falta = "1 día" if e.faltan == 1 else f"{e.faltan} días"
    return texto + f"\n<i>Faltan {falta} para que cumpla {e.años + 1}</i>"


def formatear_adios(a: Adios) -> str:
    """Respuesta de /adios."""
    dias = f"{a.dias:,}".replace(",", ".")
    años = "1 año" if a.años == 1 else f"{a.años} años"
    texto = (
        f"👻 <b>Satoshi lleva {años} sin aparecer</b>\n"
        f"Su último mensaje en el foro fue el 12/12/2010, hace {dias} días. "
        "Nunca se ha sabido quién es"
    )
    if a.faltan == 0:
        return texto + f"\n🕯️ Hoy hace {años} de su último mensaje"
    falta = "1 día" if a.faltan == 1 else f"{a.faltan} días"
    return texto + f"\n<i>Faltan {falta} para que se cumplan {a.años + 1}</i>"


def formatear_ballena(b: Ballena) -> str:
    """Respuesta de /ballena."""
    if b.btc <= 0:
        return (
            "🦠 <b>Ni gamba</b>: no tienes bitcoin en la cartera\n"
            "Si tienes, apúntalo con /compra bitcoin"
        )
    emoji, nombre = b.animal
    # Por debajo de 0,001 los decimales se comen todo, mejor en sats.
    if b.btc < 0.001:
        tienes = f"{round(b.btc * SATS_POR_BTC):,} sats".replace(",", ".")
    else:
        tienes = f"{cantidad(b.btc)} BTC"
    texto = f"{emoji} <b>Eres {_un(nombre)} {nombre}</b>\nTienes {tienes}"
    if b.siguiente is None:
        return texto + "\nNo hay nada más grande en el mar 🌊"
    emoji, nombre = b.siguiente
    return texto + f"\nPara ser {emoji} {nombre} te faltan {cantidad(b.falta)} BTC"


def _un(nombre: str) -> str:
    return "una" if nombre in ("gamba", "ballena", "ballena jorobada") else "un"


def formatear_millonario(
    coin_id: str, simbolo_cripto: str, m: Millonario, currency: str
) -> str:
    """Respuesta de /millonario."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    cripto = escape(simbolo_cripto)
    texto = (
        f"💰 <b>Para tener un millón en {nombre}</b>\n"
        f"Necesitas <b>{cantidad(m.necesitas)} {cripto}</b>, "
        f"a {simbolo}{_num(m.precio)} cada uno"
    )
    if m.hecho is not None:
        texto += (
            f"\nCon lo que tienes ({cantidad(m.tienes)} {cripto}) llevas "
            f"el <b>{m.hecho:.2f}%</b>"
        )
    return texto


def formatear_mundo(m: Mundo, currency: str) -> str:
    """Respuesta de /mundo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    personas = f"{PERSONAS // 1_000_000:,}".replace(",", ".")
    sats = f"{m.sats:,}".replace(",", ".")
    return (
        "🌍 <b>Si se repartieran todos los bitcoin</b>\n"
        f"Entre los {personas} millones de personas del mundo, a cada una le "
        f"tocarían <b>{sats} sats</b> ({_num(m.btc)} BTC)\n"
        f"Hoy serían unos <b>{simbolo}{_num(m.valor)}</b>\n"
        "<i>Nunca habrá más de 21 millones de bitcoin</i>"
    )


def formatear_pizza(p: Pizza, currency: str) -> str:
    """Respuesta de /pizza."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = (
        "🍕 El 22/05/2010 alguien pagó <b>"
        + f"{BTC:,}".replace(",", ".")
        + " BTC</b> por dos pizzas\n"
        f"Hoy serían <b>{simbolo}{grande(p.total)}</b>, "
        f"{simbolo}{grande(p.por_pizza)} cada una"
    )
    if p.aniversario == 0:
        return texto + "\n🎉 Hoy es el Bitcoin Pizza Day"
    dias = "1 día" if p.aniversario == 1 else f"{p.aniversario} días"
    return texto + f"\n<i>Faltan {dias} para el Bitcoin Pizza Day</i>"


def formatear_halving(h: Halving) -> str:
    """Respuesta de /halving."""
    ahora = f"{h.recompensa:g}".replace(".", ",")
    despues = f"{h.recompensa / 2:g}".replace(".", ",")
    dias = "1 día" if h.faltan == 1 else f"{h.faltan} días"
    # El día justo ya cuenta el siguiente, y "faltan 1458 días" sin más despista.
    hoy = "🎉 El halving toca hoy, más o menos\n\n" if h.hoy == h.anterior else ""
    return (
        f"{hoy}⛏️ <b>Próximo halving de Bitcoin</b>\n"
        f"Faltan <b>{dias}</b>, hacia el {h.siguiente:%d/%m/%Y}\n"
        f"{barra(h.hecho)}  {h.hecho:.0f}% del ciclo\n"
        f"Lo que se paga por bloque bajará de {ahora} a {despues} BTC\n"
        "<i>La fecha es aproximada: depende de lo rápido que salgan los bloques</i>"
    )


def formatear_redondo(redondos: list[tuple[str, Redondo]], currency: str) -> str:
    """Respuesta de /redondo, con una o varias."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    bloques = []
    for coin_id, r in redondos:
        nombre = escape(coin_id.replace("-", " ").title())
        bloques.append(
            f"🎯 <b>{nombre}</b>  ahora {simbolo}{_num(r.ahora)}\n"
            f"⬆️ {simbolo}{_num(r.arriba)}  a <b>{r.falta_arriba:+.2f}%</b>\n"
            f"⬇️ {simbolo}{_num(r.abajo)}  a <b>{r.falta_abajo:+.2f}%</b>"
        )
    return "\n\n".join(bloques)


def formatear_dia(coin_id: str, d: Dia, currency: str, hoy: date | None = None) -> str:
    """Respuesta de /dia."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    hoy = hoy or date.today()
    if d.fecha == hoy:
        cuando, precio = "hoy", "Va por"
    else:
        formato = "%d/%m" if d.fecha.year == hoy.year else "%d/%m/%Y"
        semana = NOMBRES[d.fecha.weekday()].lower()
        cuando, precio = f"el {semana} {d.fecha:{formato}}", "Cerró a"

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
    texto += f"Máximo {_num(r.maximo)} · Mínimo {_num(r.minimo)}\n"
    if r.posicion is not None:
        texto += (
            f"<code>mín {barra(r.posicion)} máx</code> al {r.posicion:.0f}% del rango\n"
        )
    texto += (
        f"\n<i>Si sube, a {n1} le ha ido mejor que a {n2}. "
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
    grande = demasiado(trozos)
    if grande:
        nombre = escape(grande.coin_id.replace("-", " ").title())
        lineas.append(
            f"\n⚖️ Más de la mitad es <b>{nombre}</b>. "
            "Si cae, lo notará toda la cartera."
        )
    return "\n".join(lineas)


def formatear_rebalanceo(
    pasos: list[Paso], total: float, currency: str, iguales: bool
) -> str:
    """Respuesta de /rebalanceo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    titulo = "a partes iguales" if iguales else "en tu reparto"
    lineas = [
        f"⚖️ <b>Para dejar tu cartera {titulo}</b>",
        f"Ahora vale {simbolo}{_num(total)}",
        "",
    ]
    for p in pasos:
        nombre = escape(p.coin_id.replace("-", " ").title())
        cambio = f"{p.peso:.0f}% → {p.objetivo:.0f}%"
        if not p.mover:
            lineas.append(f"✅ {nombre} ya está bien: {p.peso:.0f}%")
        elif not p.objetivo:
            lineas.append(
                f"💸 Vende toda la de {nombre}: {texto_cantidad(p.cantidad)}, "
                f"<b>{simbolo}{_num(p.ahora)}</b> · {cambio}"
            )
        else:
            verbo = "🛒 Compra" if p.mover > 0 else "💸 Vende"
            lineas.append(
                f"{verbo} <b>{simbolo}{_num(abs(p.mover))}</b> de {nombre} "
                f"({texto_cantidad(p.cantidad)}) · {cambio}"
            )
    if all(not p.mover for p in pasos):
        lineas = lineas[:2] + ["", "👌 Ya la tienes así, no hay nada que mover"]

    pie = "Al precio de ahora y sin contar comisiones."
    if iguales:
        pie += f" Para otro reparto: {EJEMPLO_REBALANCEO}"
    lineas += ["", f"<i>{pie}</i>"]
    return "\n".join(lineas)


def formatear_rango(
    coin_id: str,
    r: Rango,
    horas: float,
    currency: str,
    desde: datetime | None = None,
    ahora: datetime | None = None,
) -> str:
    """Respuesta de /rango. desde va si no hay precios de todo el tramo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    del_maximo = (r.ahora / r.maximo - 1) * 100
    del_minimo = (r.ahora / r.minimo - 1) * 100
    de_la_media = (r.ahora / r.media - 1) * 100

    def hace_cuanto(fecha: datetime) -> str:
        momento = fecha.astimezone()
        cuanto = hace(fecha, ahora or datetime.now(momento.tzinfo))
        return f"el {momento:%d/%m}{'' if cuanto == 'hoy' else ', ' + cuanto}"

    texto = (
        f"📏 <b>{nombre}</b>, {nombre_periodo(horas)}\n\n"
        f"Máximo {simbolo}{_num(r.maximo)}  <i>{hace_cuanto(r.cuando_maximo)}"
        f" · ahora {del_maximo:+.2f}%</i>\n"
        f"Mínimo {simbolo}{_num(r.minimo)}  <i>{hace_cuanto(r.cuando_minimo)}"
        f" · ahora {del_minimo:+.2f}%</i>\n"
        f"Media {simbolo}{_num(r.media)}  <i>ahora {de_la_media:+.2f}%</i>\n"
    )
    # Sin moverse sería un 0% que no dice nada; ya sale abajo.
    if r.posicion is not None:
        texto += f"<i>Del mínimo al máximo, {r.amplitud:+.2f}%</i>\n"
    texto += f"\nAhora <b>{simbolo}{_num(r.ahora)}</b>"
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
    coin_id: str,
    c: Caida,
    horas: float,
    currency: str,
    desde: datetime | None = None,
    ahora: datetime | None = None,
) -> str:
    """Respuesta de /caida. desde va si no hay precios de todo el tramo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = "Tu cartera" if coin_id == CARTERA else _nombre(coin_id)
    momento = c.cuando_maximo.astimezone()
    cuanto = hace(c.cuando_maximo, ahora or datetime.now(momento.tzinfo))

    texto = f"📉 <b>{nombre}</b>, {nombre_periodo(horas)}\n\n"
    if c.desde_maximo == 0:
        texto += f"Ahora <b>{simbolo}{_num(c.ahora)}</b>, está en su máximo del tramo\n"
    else:
        texto += (
            f"Ahora <b>{simbolo}{_num(c.ahora)}</b>, "
            f"<b>{c.desde_maximo:+.2f}%</b> desde el máximo\n"
            f"<i>Máximo {simbolo}{_num(c.maximo)} el {momento:%d/%m}"
            f"{'' if cuanto == 'hoy' else ', ' + cuanto}</i>\n"
            f"Para volver al máximo tiene que subir un "
            f"<b>{c.para_recuperar:+.2f}%</b>\n"
        )
    if c.peor == 0:
        texto += "\nNo ha tenido ninguna caída en este tramo"
    else:
        texto += (
            f"\nPeor caída <b>{c.peor:+.2f}%</b>: de {simbolo}{_num(c.pico)} el "
            f"{c.cuando_pico.astimezone():%d/%m} a {simbolo}{_num(c.valle)} el "
            f"{c.cuando_valle.astimezone():%d/%m}"
        )
        texto += "\n" + _recuperacion(c, simbolo)
    if desde is not None:
        cuando = desde.astimezone()
        texto += f"\n<i>Solo tengo precios desde el {cuando:%d/%m a las %H:%M}.</i>"
    return texto


def _recuperacion(c: Caida, simbolo: str) -> str:
    if c.recuperado is None:
        return f"Aún no ha vuelto a {simbolo}{_num(c.pico)}"
    tardo = c.recuperado - c.cuando_pico
    if tardo.days == 0:
        cuanto = "en menos de un día"
    else:
        cuanto = f"en {tardo.days} {'día' if tardo.days == 1 else 'días'}"
    return f"Volvió a ese precio {cuanto}, el {c.recuperado.astimezone():%d/%m}"


def formatear_sube(
    coin_id: str,
    s: Subida,
    horas: float,
    currency: str,
    desde: datetime | None = None,
    ahora: datetime | None = None,
) -> str:
    """Respuesta de /sube. desde va si no hay precios de todo el tramo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    momento = s.cuando_minimo.astimezone()
    cuanto = hace(s.cuando_minimo, ahora or datetime.now(momento.tzinfo))

    texto = f"🚀 <b>{nombre}</b>, {nombre_periodo(horas)}\n\n"
    if s.desde_minimo == 0:
        texto += f"Ahora <b>{simbolo}{_num(s.ahora)}</b>, está en su mínimo del tramo\n"
    else:
        texto += (
            f"Ahora <b>{simbolo}{_num(s.ahora)}</b>, "
            f"<b>{s.desde_minimo:+.2f}%</b> desde el mínimo\n"
            f"<i>Mínimo {simbolo}{_num(s.minimo)} el {momento:%d/%m}"
            f"{'' if cuanto == 'hoy' else ', ' + cuanto}</i>\n"
            f"Para volver al mínimo tendría que bajar un "
            f"<b>{s.para_volver:+.2f}%</b>\n"
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
    coin_id: str,
    e: Extremo,
    horas: float,
    currency: str,
    desde: date | None = None,
    hoy: date | None = None,
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
            cuanto = hace(d.dia, hoy or date.today())
            texto += (
                f"\n{_flecha(d.cambio)} {titulo}: <b>{d.cambio:+.2f}%</b> "
                f"el {d.dia:%d/%m}{'' if cuanto == 'hoy' else ', ' + cuanto}\n"
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
    )
    if len(v.ultimos) > 1:
        cuadros = "".join(
            {True: "🟩", False: "🟥", None: "⬜"}[sube] for sube in v.ultimos
        )
        texto += f"Últimos {len(v.ultimos)} días: {cuadros}\n"
    texto += "<i>Con el precio del final de cada día</i>"
    if incompleto:
        texto += f"\n<i>Solo tengo precios desde el {v.desde:%d/%m}.</i>"
    return texto


def formatear_diasemana(
    coin_id: str,
    s: DiasSemana,
    horas: float,
    incompleto: bool = False,
    hoy: date | None = None,
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
    de_hoy = s.de(hoy or date.today())
    if de_hoy:
        texto += f"Hoy es {de_hoy.nombre.lower()}: suele ir {de_hoy.media:+.2f}%"
        if len(s.dias) > 1 and de_hoy == s.mejor:
            texto += ", su mejor día"
        elif len(s.dias) > 1 and de_hoy == s.peor:
            texto += ", su peor día"
        texto += "\n"
    texto += "<i>Lo que cambia de media ese día y cuántas veces lo he visto</i>"
    if incompleto:
        texto += f"\n<i>Solo tengo precios desde el {s.desde:%d/%m}.</i>"
    return texto


def formatear_horas(
    coin_id: str, h: Horas, horas: float, ahora: datetime | None = None
) -> str:
    """Respuesta de /horas."""
    nombre = escape(coin_id.replace("-", " ").title())
    barata, cara = h.medias[h.barata], h.medias[h.cara]
    texto = (
        f"🕐 <b>{nombre}</b> por horas, {nombre_periodo(horas)}\n\n"
        f"🟢 Más barata sobre las <b>{h.barata:02d}:00</b> ({barata:+.2f}%)\n"
        f"🔴 Más cara sobre las <b>{h.cara:02d}:00</b> ({cara:+.2f}%)\n"
    )
    if h.ahorro > 0:
        texto += (
            f"Comprando a las {h.barata:02d}:00 y no a las {h.cara:02d}:00, "
            f"un <b>{h.ahorro:.2f}%</b> más barato\n"
        )
    hora = (ahora or datetime.now()).astimezone().hour
    if hora in h.medias:
        media = h.medias[hora]
        if media < 0:
            como = "más barata que la media del día"
        elif media > 0:
            como = "más cara que la media del día"
        else:
            como = "justo en la media del día"
        texto += (
            f"\nAhora son las {hora:02d}:00: a esta hora suele estar "
            f"{media:+.2f}%, {como}\n"
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


def formatear_doble(c: CarteraDoble, currency: str) -> str:
    """Respuesta de /doble."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["✌️ <b>Para doblar lo que metiste</b>", ""]
    for d in c.criptos:
        nombre = escape(d.coin_id.replace("-", " ").title())
        if d.falta > 0:
            como = f"falta <b>{d.falta:+.2f}%</b>"
        else:
            como = "ya lo has doblado"
        texto.append(
            f"{'🔴' if d.falta > 0 else '🟢'} <b>{nombre}</b> a "
            f"{simbolo}{_num(d.objetivo)} · {como}"
        )
        texto.append(
            f"   <i>ahora {simbolo}{_num(d.precio)}, te salió a "
            f"{simbolo}{_num(d.medio)}</i>"
        )

    if c.total is not None:
        if c.total > 0:
            texto.append(f"\n📦 Todo junto tendría que subir un <b>{c.total:+.2f}%</b>")
        else:
            texto.append("\n📦 Todo junto ya lo has doblado 🎉")
    if c.sin_coste:
        nombres = ", ".join(escape(x.replace("-", " ").title()) for x in c.sin_coste)
        texto.append(f"\n<i>De {nombres} no sé lo que te costó.</i>")
    return "\n".join(texto)


def formatear_mitad(c: CarteraMitad, currency: str) -> str:
    """Respuesta de /mitad."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🪓 <b>Para perder la mitad de lo que metiste</b>", ""]
    for m in c.criptos:
        nombre = escape(m.coin_id.replace("-", " ").title())
        if m.aguanta > 0:
            como = f"aguanta <b>{-m.aguanta:+.2f}%</b>"
        else:
            como = "ya está por debajo"
        texto.append(
            f"{'🟢' if m.aguanta > 0 else '🔴'} <b>{nombre}</b> a "
            f"{simbolo}{_num(m.objetivo)} · {como}"
        )
        texto.append(
            f"   <i>ahora {simbolo}{_num(m.precio)}, te salió a "
            f"{simbolo}{_num(m.medio)}</i>"
        )

    if c.total is not None:
        if c.total > 0:
            texto.append(
                f"\n📦 Todo junto aguanta una bajada del <b>{c.total:.2f}%</b>"
            )
        else:
            texto.append("\n📦 Todo junto ya vale menos de la mitad de lo que metiste")
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


def formatear_meta(m: Meta, currency: str) -> str:
    """Respuesta de /meta."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [f"🏁 <b>Tu cartera hacia {simbolo}{_num(m.meta)}</b>"]
    if m.falta <= 0:
        texto.append(
            f"🎉 Ya está: vale {simbolo}{_num(m.valor)}, "
            f"{simbolo}{_num(-m.falta)} por encima"
        )
        return "\n".join(texto)

    texto.append(f"Vale {simbolo}{_num(m.valor)}")
    texto.append(f"{barra(m.hecho)}  {m.hecho:.0f}% del camino")
    texto.append(
        f"Te faltan <b>{simbolo}{_num(m.falta)}</b>: tiene que subir un "
        f"<b>{m.cambio:+.2f}%</b>"
    )
    # Desde x2 se entiende mejor así que con un +250%.
    if m.veces >= 2:
        texto.append(f"<i>O sea, multiplicarse por {_es(f'{m.veces:,.1f}')}</i>")
    return "\n".join(texto)


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
        f"<i>Habrías comprado {texto_cantidad(cantidad / antes)} {nombre}</i>\n"
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
    de_golpe: float | None = None,
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
    # Con una compra sola es lo mismo, no hay nada que comparar.
    if de_golpe and compras > 1:
        diferencia = valor - de_golpe
        texto += (
            f"\n\n📦 Todo de golpe en la primera: {simbolo}{_num(de_golpe)} "
            f"({(de_golpe / invertido - 1) * 100:+.2f}%)\n"
        )
        if abs(diferencia) < 0.01:
            texto += "Te habría dado lo mismo"
        elif diferencia > 0:
            texto += f"Mejor poco a poco, por {simbolo}{_num(diferencia)}"
        else:
            texto += f"Mejor de golpe, por {simbolo}{_num(-diferencia)}"
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
    volumen: float | None = None,
    puesto: int | None = None,
    sats: float | None = None,
    rango_24h: tuple[float, float] | None = None,
    emitido: tuple[float, float] | None = None,
    maximo: Maximo | None = None,
    ahora: datetime | None = None,
    en_30d: float | None = None,
    capitalizacion: float | None = None,
) -> str:
    """Respuesta de /precio: lo que vale ahora y cómo va en 1 h, 24 h, 7 y 30 días.

    tuyo es lo que tienes de ella, si esta en la cartera. dia, los precios
    guardados de las últimas 24 h, para las barritas."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    texto = f"💰 <b>{nombre}</b>  {simbolo}{_num(precio)}"
    if sats is not None:
        # Por debajo de un sat, redondear daría "0 sats", que no es verdad.
        en_sats = texto_cantidad(round(sats)) if sats >= 1 else _num(sats)
        texto += f"  <i>({en_sats} sats)</i>"
    if en_1h is not None:
        texto += f"\n{_flecha(en_1h)} {en_1h:+.2f}% en 1 h"
    if variacion is None:
        texto += "\n<i>Sin datos de las últimas 24 h</i>"
    else:
        texto += f"\n{_flecha(variacion)} {variacion:+.2f}% en 24 h"
    if en_7d is not None:
        texto += f"\n{_flecha(en_7d)} {en_7d:+.2f}% en 7 días"
    if en_30d is not None:
        texto += f"\n{_flecha(en_30d)} {en_30d:+.2f}% en 30 días"
    if rango_24h is not None:
        bajo, alto = rango_24h
        texto += (
            f"\n<i>Mínimo {simbolo}{_num(bajo)} · máximo {simbolo}{_num(alto)}"
            " en 24 h</i>"
        )
    datos = []
    if puesto is not None:
        datos.append(f"Puesto #{puesto}")
    if volumen is not None:
        texto_volumen = f"volumen en 24 h: {simbolo}{grande(volumen)}"
        # Para ver si hoy se mueve mucho para lo grande que es.
        if capitalizacion:
            texto_volumen += (
                f" ({_peso(volumen / capitalizacion * 100)} de lo que vale)"
            )
        datos.append(texto_volumen)
    if datos:
        linea = " · ".join(datos)
        texto += f"\n<i>{linea[0].upper()}{linea[1:]}</i>"
    if emitido is not None:
        porcentaje, tope = emitido
        texto += f"\n<i>Emitido el {porcentaje:.1f}% de {grande(tope)}</i>"
    if maximo is not None:
        if not maximo.falta():
            texto += "\n🎉 <i>Está en su máximo histórico</i>"
        else:
            cuando = hace(maximo.fecha, ahora or datetime.now(maximo.fecha.tzinfo))
            texto += (
                f"\n<i>Máximo histórico {simbolo}{_num(maximo.maximo)} {cuando}"
                f" · le falta +{maximo.falta():.2f}%</i>"
            )
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
        texto += "🎉 está en máximos"
    else:
        texto += f"le falta +{m.falta():.2f}% para volver"
    subido = m.desde_minimo()
    if subido is None:
        return texto
    return texto + (
        f"\n\n🕳 Mínimo histórico {simbolo}{_num(m.minimo)}\n"
        f"<i>El {m.fecha_minimo.astimezone():%d/%m/%Y}, "
        f"{hace(m.fecha_minimo, ahora)}</i> · ha subido +{subido:.2f}% desde ahí"
    )


def formatear_maximos(
    maximos: list[Maximo], faltan: list[str], currency: str, ahora: datetime
) -> str:
    """/ath de varias, una por linea."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🏔 <b>Máximo histórico</b> · <i>lo que le falta</i>", ""]
    for m in maximos:
        nombre = escape(m.coin_id.replace("-", " ").title())
        falta = f"+{m.falta():.2f}%" if m.falta() else "🎉 en máximos"
        texto.append(
            f"<b>{nombre}</b>  {simbolo}{_num(m.maximo)} "
            f"<i>({hace(m.fecha, ahora)})</i>  {falta}"
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


def formatear_ultimo(
    lista: list[Ultimo], currency: str, ahora: datetime | None = None
) -> str:
    """/ultimo: cuándo avisó cada una y cuánto se ha movido desde entonces."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🔔 <b>El último aviso de cada una</b>"]
    for u in lista:
        nombre = escape(u.coin_id.replace("-", " ").title())
        texto.append("")
        if u.aviso is None:
            texto.append(f"<b>{nombre}</b>  <i>aún no ha avisado</i>")
            continue

        momento = u.aviso.cuando.astimezone()
        cuanto = hace(u.aviso.cuando, ahora or datetime.now(momento.tzinfo))
        if cuanto == "hoy":
            cuando = f"hoy a las {momento:%H:%M}"
        else:
            cuando = f"{cuanto}, el {momento:%d/%m a las %H:%M}"
        texto.append(f"<b>{nombre}</b>  {cuando}")
        linea = (
            f"{'🔺 Subió' if u.aviso.sube else '🔻 Bajó'} a "
            f"{simbolo}{_num(u.aviso.precio)}"
        )
        if u.desde_entonces is not None:
            linea += f"  ·  desde entonces {u.desde_entonces:+.2f}%"
        texto.append(linea)
    return "\n".join(texto)


def formatear_aleatoria(puesto: int, m: Movida, currency: str) -> str:
    """/aleatoria: la que ha tocado, con su puesto y cómo va hoy."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    flecha = "🔺" if m.variacion >= 0 else "🔻"
    nombre = escape(m.nombre)
    # Sin el símbolo si es el mismo nombre: "NEXO (NEXO)" queda raro.
    if m.simbolo and m.simbolo != m.nombre.upper():
        nombre += f" ({escape(m.simbolo)})"
    return (
        f"🎲 <b>{nombre}</b>\n"
        f"Es la número {puesto} por tamaño\n"
        f"Vale {simbolo}{_num(m.precio)}  ·  En 24 h: {flecha} {m.variacion:+.2f}%\n"
        f"<i>Para vigilarla: /vigilar {escape(m.coin_id)} %5</i>"
    )


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
    for dias, cuando in ((1, "Ayer"), (7, "Hace una semana"), (30, "Hace un mes")):
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
            ("El resto", m.resto),
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


def formatear_quieta(quietas: list[Quieta], currency: str) -> str:
    """Respuesta de /quieta: la más tranquila arriba y el resto debajo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    q = quietas[0]
    nombre = escape(q.coin_id.replace("-", " ").title())
    texto = [
        f"😴 <b>La más quieta en 24 h: {nombre}</b>",
        f"Se ha movido entre {simbolo}{_num(q.minimo)} y {simbolo}{_num(q.maximo)}, "
        f"un <b>{q.rango:.2f}%</b>",
    ]
    if len(quietas) > 1:
        texto.append("")
        for o in quietas[1:]:
            otra = escape(o.coin_id.replace("-", " ").title())
            texto.append(f"· {otra}  {o.rango:.2f}%")
    texto.append("\n<i>Del mínimo al máximo, con lo que tengo guardado</i>")
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

    junta = media_comparar(resultados)
    if junta is not None:
        texto += ["", f"De media {_flecha(junta)} <b>{junta:+.2f}%</b>"]

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
    recomendado: int | None = None,
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
    if recomendado is not None:
        texto += [
            "",
            f"👉 Para que te avise un par de veces a la semana como mucho: "
            f"<code>/vigilar {escape(coin_id)} %{recomendado}</code>",
        ]
    if desde:
        texto.append(f"\n<i>Solo tengo precios desde el {desde.astimezone():%d/%m}</i>")
    return "\n".join(texto)


def formatear_no_encuentro(coin_ids: list[str]) -> str:
    nombres = ", ".join(f"<b>{escape(c)}</b>" for c in coin_ids)
    return (
        f"No encuentro {nombres} en CoinGecko. Prueba con /buscar {escape(coin_ids[0])}"
    )


def formatear_semana(
    semana: Semana,
    currency: str,
    desde: datetime | None = None,
    titulo: str = "📅 <b>Tu semana</b>",
    tramo: str = "en la semana",
    pista: str | None = None,
) -> str:
    """El resumen de los domingos y /mes. desde va solo si falta el principio."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [titulo, ""]

    linea = f"Tu cartera vale <b>{simbolo}{_num(semana.fin)}</b>"
    if semana.porcentaje is not None:
        signo = "+" if semana.ganancia >= 0 else "-"
        linea += (
            f"\n{_flecha(semana.porcentaje)} {semana.porcentaje:+.2f}% "
            f"({signo}{simbolo}{_num(abs(semana.ganancia))}) {tramo}"
        )
    texto.append(linea)

    if desde is not None:
        cuando = desde.astimezone()
        texto.append(f"<i>Solo tengo precios desde el {cuando:%d/%m a las %H:%M}.</i>")
        if pista:
            texto.append(f"<i>{escape(pista)}</i>")

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


def _hora(hora: time) -> str:
    return f"{hora.hour}:{hora.minute:02d}"


def _nombre(coin_id: str) -> str:
    return escape(coin_id.replace("-", " ").title())


def formatear_recordatorio(
    r: Recordatorio, precio: float, currency: str, hora: time
) -> str:
    """Respuesta al poner un /recordar."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    return (
        f"📅 Cada <b>{r.nombre_dia}</b> a las {_hora(hora)} te recuerdo comprar "
        f"<b>{simbolo}{_num(r.importe)}</b> de <b>{_nombre(r.coin_id)}</b>.\n"
        f"A precio de hoy ({simbolo}{_num(precio)}) serían "
        f"{texto_cantidad(r.importe / precio)}.\n"
        f"Para quitarlo: /recordar {escape(r.coin_id)} no"
    )


def formatear_recordatorios(
    lista: list[Recordatorio], currency: str, hora: time
) -> str:
    """/recordar a secas."""
    if not lista:
        return (
            "No tienes ningún recordatorio. Para que te avise cada semana de tu "
            "compra: /recordar lunes 50 btc"
        )
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    lineas = [f"📅 <b>Tus compras de cada semana</b> <i>(a las {_hora(hora)})</i>", ""]
    for r in lista:
        lineas.append(
            f"<b>{r.nombre_dia.capitalize()}</b>: {simbolo}{_num(r.importe)} "
            f"de {_nombre(r.coin_id)}"
        )
    lineas += ["", "Para quitar uno: /recordar btc no"]
    return "\n".join(lineas)


def formatear_toca_comprar(r: Recordatorio, precio: float, currency: str) -> str:
    """El aviso del día que toca."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    return (
        f"📅 <b>Toca tu compra de {_nombre(r.coin_id)}</b>\n"
        f"Tus {simbolo}{_num(r.importe)} de cada {r.nombre_dia}: a "
        f"{simbolo}{_num(precio)} son <b>{texto_cantidad(r.importe / precio)}</b>.\n"
        "Cuando la hagas, dale al botón y la apunto en la cartera."
    )


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
        hecho = progreso(alerta, precio)
        if hecho is not None:
            texto += f"\n{_barra_progreso(hecho)} del camino"
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


def _stop_quien(s: Stop) -> tuple[str, str, str]:
    """El nombre, lo que costó y cómo se dice lo de ahora, para /stop."""
    if s.coin_id == CARTERA:
        return "tu cartera", "lo que metiste", "Ahora vale"
    return (
        escape(s.coin_id.replace("-", " ").title()),
        "lo que te costó",
        "Ahora está a",
    )


def formatear_stop(s: Stop, numero: int, currency: str) -> str:
    """Respuesta al crear un /stop."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre, coste, ahora = _stop_quien(s)
    emoji, verbo, lado = (
        ("🎯", "sube", "por encima") if s.sube else ("🛑", "baja", "por debajo")
    )
    media = "" if s.coin_id == CARTERA else " de media"
    texto = (
        f"{emoji} Te aviso si <b>{nombre}</b> {verbo} a "
        f"<b>{simbolo}{_num(s.objetivo)}</b>, un {_pct(abs(s.porcentaje))}% {lado} "
        f"de {coste} ({simbolo}{_num(s.coste)}{media}).\n"
        f"{ahora} {simbolo}{_num(s.ahora)}: vas {_signo(s.llevas)}. "
        "Solo te aviso una vez.\n"
        f"Es la número {numero} de /alertas."
    )
    if s.coin_id != CARTERA:
        # El objetivo se queda fijo; si compras más, ya no es tu precio medio.
        texto += (
            "\n<i>Si compras o vendes, tu precio medio cambia: vuelve a ponerlo.</i>"
        )
    return texto


def formatear_stop_pasado(s: Stop) -> str:
    """/stop a un % por el que ya has pasado: saltaría en el siguiente ciclo."""
    nombre, coste, _ = _stop_quien(s)
    return (
        f"Con <b>{nombre}</b> ya vas {_signo(s.llevas)} sobre {coste}, "
        f"más allá del {_pct(s.porcentaje)}%. Ponlo más lejos o mira /cartera"
    )


def _signo(porcentaje: float) -> str:
    return f"{porcentaje:+.1f}%".replace(".", ",")


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
    alertas: list[Puntual],
    currency: str,
    precios: dict[str, float] | None = None,
    ahora: datetime | None = None,
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
        hecho = progreso(a, (precios or {}).get(a.coin_id))
        if hecho is not None:
            lineas.append(f"      {_barra_progreso(hecho)}")
        if a.creada:
            puesta = hace(a.creada, ahora or datetime.now(a.creada.tzinfo))
            lineas.append(f"      🕐 <i>puesta {puesta}</i>")
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


def _barra_progreso(porcentaje: float) -> str:
    """'<code>▓▓▓▓▓▓▓░░░</code> 68%'."""
    # Con floor un 99% no se ve lleno, que es lo que es: aún no ha llegado.
    llenas = math.floor(porcentaje / 10)
    return f"<code>{'▓' * llenas}{'░' * (10 - llenas)}</code> {math.floor(porcentaje)}%"


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
