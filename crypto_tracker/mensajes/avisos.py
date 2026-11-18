"""Decide si hay que avisar y escribe el aviso de cuando cruza un nivel."""

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..condicion import Condicion
from ..config import Watch
from ..puntuales import CARTERA
from ..telegram import escape
from .base import (
    ALTO,
    BAJO,
    FUENTE,
    NORMAL,
    SIMBOLOS,
    _flecha,
    _minutos,
    _num,
    _quien_condicion,
)

# Solo para el tipo: esos módulos importan de alerts y se haría un círculo.
if TYPE_CHECKING:
    from ..contexto import Contexto

logger = logging.getLogger(__name__)


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
    contexto: "Contexto | None" = None  # lo que pasó otras veces que se movió así
    condicion: tuple[Condicion, float] | None = None  # la de /alerta y su valor


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
    if alerta.contexto:
        texto += "\n" + _linea_contexto(alerta.contexto)
    if alerta.falta_maximo == 0:
        texto += "\n🎉 <i>Está en su máximo histórico</i>"
    elif alerta.falta_maximo is not None:
        texto += (
            f"\n<i>Le falta +{alerta.falta_maximo:.2f}% para su máximo histórico</i>"
        )
    if alerta.condicion:
        c, valor = alerta.condicion
        texto += f"\n✅ {_quien_condicion(c)} en {valor:.0f}, como pedías"
    if alerta.nota:
        texto += f"\n📝 {escape(alerta.nota)}"
    if alerta.puntual:
        texto += "\n<i>Era tu /alerta, ya la he quitado.</i>"
    return texto


def _linea_contexto(c: "Contexto") -> str:
    verbo, sigue = ("subió", "subiendo") if c.sube else ("cayó", "bajando")
    return (
        f"📚 <i>En {c.dias} días {verbo} más de un {c.desde:.1f}% en un día "
        f"{c.veces} veces: a la semana estaba {c.media:+.1f}% de media y en "
        f"{c.siguio} de {c.veces} siguió {sigue}</i>"
    )


def con_fuente(texto: str) -> str:
    return f"{texto}\n\n{FUENTE}"


def formatear_varios(alertas: list[Alert], currency: str) -> str:
    """Junta varios avisos en un mensaje. Uno solo se manda tal cual."""
    if len(alertas) == 1:
        return formatear(alertas[0], currency)

    cuerpo = "\n\n".join(formatear(a, currency) for a in alertas)
    return f"<b>{len(alertas)} avisos</b>\n\n{cuerpo}"
