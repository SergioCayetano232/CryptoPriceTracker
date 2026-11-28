"""Los mensajes de la cartera: resumen, compras, ventas e impuestos."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from ..arrepentido import Arrepentido
from ..calendario import Mes
from ..cartera import Valor, mejor_y_peor, peso
from ..comisiones import Comisiones
from ..compras import Compra, Resumen
from ..concentracion import Concentracion
from ..config import Posicion
from ..corregir import CANTIDAD, Correccion
from ..cruce import ARRIBA, CORTA, LARGA, Cruce
from ..cuenta_binance import Comparacion
from ..deposito import Contra as ContraDeposito
from ..estables import Desvio
from ..ganancias import Ganancias
from ..hacienda.compensar import Compensacion
from ..hacienda.impuestos import Impuestos
from ..hacienda.modelo721 import LIMITE as LIMITE_721
from ..hacienda.modelo721 import SUBIDA as SUBIDA_721
from ..hacienda.modelo721 import Modelo721
from ..hacienda.permuta import Permuta
from ..hacienda.sivendo import Simulacion
from ..hodl import Hodl
from ..hoy import Hoy
from ..hoy import mejor_y_peor as extremos_hoy
from ..ideal import Ideal, Parte, fuera
from ..ideal import comando as comando_ideal
from ..importar import Operacion
from ..inflacion import Inflacion
from ..informes.aniversario import MAX as MAX_ANIVERSARIOS
from ..informes.aniversario import Aniversario
from ..informes.anual import Año
from ..informes.mes import MESES
from ..mercado import grande
from ..movimientos import (
    Movimiento,
    descuadre,
    precio_medio,
    recibido,
    texto_cantidad,
    totales,
)
from ..pelotazo import Jugada, Pelotazo
from ..periodo import nombre as nombre_periodo
from ..primera import Primera
from ..record import Record
from ..rellenar import Relleno
from ..rentabilidad import MIN_DIAS as MIN_DIAS_RENTABILIDAD
from ..rentabilidad import Rentabilidad
from ..riesgo import CAIDA as CAIDA_RIESGO
from ..riesgo import Riesgo
from ..rsi import PERIODO, SOBRECOMPRA, Rsi
from ..telegram import escape
from ..volumen import Volumen
from ..vsbolsa import Contra as ContraBolsa
from ..vsbtc import Contra
from .base import (
    BARRAS_MOVIL,
    SIMBOLOS,
    _decimal,
    _es,
    _flecha,
    _ganancia,
    _nombre,
    _num,
    _pct,
    _peso,
    _signo,
    _siguiente,
    _veces,
    muestrear,
    sparkline,
)

# Solo para el tipo: esos módulos importan de alerts y se haría un círculo.
if TYPE_CHECKING:
    from ..timing import Compra as CompraTiming
    from ..timing import Timing


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


def _puntos(valor: float) -> str:
    texto = f"{abs(valor):.1f}".replace(".", ",").removesuffix(",0")
    return f"{texto} punto" if texto == "1" else f"{texto} puntos"


def _parte(p: Parte) -> str:
    nombre = escape(p.coin_id.replace("-", " ").title())
    linea = f"<b>{nombre}</b> {p.peso:.0f}% · querías {p.objetivo:.0f}%"
    # Por debajo de medio punto ya está donde querías.
    if abs(p.puntos) < 0.5:
        return linea
    verbo = "le sobran" if p.puntos > 0 else "le faltan"
    # Sin decimales, como los % de al lado: 87% contra 60% son 27, no 26,8.
    return f"{linea} · {verbo} {_puntos(round(p.puntos))}"


def formatear_aviso_ideal(lista: list[Parte], ideal: Ideal) -> str:
    """El aviso de /ideal: solo las que se han salido del margen."""
    return "\n".join(
        [
            "⚖️ <b>Tu cartera se ha alejado de tu reparto</b>",
            *(_parte(p) for p in fuera(lista, ideal.margen)),
            "Para volver, mira qué mover con:",
            f"<code>{escape(comando_ideal(ideal.reparto))}</code>",
        ]
    )


def formatear_ideal(ideal: Ideal, lista: list[Parte]) -> str:
    """Respuesta de /ideal. Sin lista (no hay precios), solo lo que quieres."""
    texto = ["⚖️ <b>Tu reparto ideal</b>"]
    if lista:
        for p in lista:
            marca = "⚠️ " if abs(p.puntos) >= ideal.margen else ""
            texto.append(marca + _parte(p))
    else:
        for coin_id, pct in ideal.reparto.items():
            nombre = escape(coin_id.replace("-", " ").title())
            texto.append(f"<b>{nombre}</b> {pct:.0f}%")
    texto += [
        "",
        f"<i>Aviso cuando alguna se aleje {_puntos(ideal.margen)}. "
        "Para quitarlo: /ideal no</i>",
    ]
    return "\n".join(texto)


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


def formatear_cruce(c: Cruce, currency: str) -> str:
    """El aviso de AVISO_CRUCE."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(c.coin_id.replace("-", " ").title())
    if c.lado == ARRIBA:
        cabecera = f"🌟 <b>Cruz dorada en {nombre}</b>"
        detalle = f"La media de {CORTA} días pasa por encima de la de {LARGA}"
        lectura = "Suele leerse como que empieza una racha buena"
    else:
        cabecera = f"☠️ <b>Cruz de la muerte en {nombre}</b>"
        detalle = f"La media de {CORTA} días pasa por debajo de la de {LARGA}"
        lectura = "Suele leerse como que empieza una racha mala"
    return "\n".join(
        [
            cabecera,
            f"{detalle}: {simbolo}{_num(c.corta)} contra {simbolo}{_num(c.larga)}",
            f"Ahora {simbolo}{_num(c.ahora)}",
            f"<i>{lectura}, pero llega tarde y falla a menudo</i>",
        ]
    )


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


VEREDICTO_TIMING = {
    "ojo": "Tienes buen ojo (o buena suerte): sueles comprar en los días baratos",
    "caro": "Sueles comprar en los días caros. Repartir en días fijos te iría mejor: "
    "/recordar o /pienso",
    "azar": "Más o menos como comprar un día cualquiera: el momento ni te da ni te "
    "quita",
}


def formatear_timing(t: "Timing", currency: str, coin_id: str | None) -> str:
    """/timing: tus compras contra la media de los días de alrededor."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    de = f" de {_nombre(coin_id)}" if coin_id else ""
    n = len(t.compras)
    texto = [f"⏱️ <b>¿Aciertas el momento{de}?</b>", ""]
    if n == 1:
        cual = "más barata" if t.baratas else "más cara"
        texto.append(f"Tu compra fue {cual} que la media de los días de alrededor")
    else:
        texto.append(
            f"De {n} compras, <b>{t.baratas}</b> fueron más baratas que la media de "
            "los días de alrededor"
        )
    menos = "menos" if t.ahorro >= 0 else "más"
    texto.append(
        f"Pagaste un <b>{abs(t.ahorro):.1f}% {menos}</b> que comprando un día "
        "cualquiera de esas semanas"
    )
    if t.posicion is not None:
        texto.append(
            f"Compraste de media en el <b>{t.posicion:.0f}</b> de 100 de lo que se "
            "movió alrededor (0, el día más barato; 100, el más caro)"
        )
    texto += ["", f"👉 {VEREDICTO_TIMING[t.veredicto]}"]

    if n > 1:
        texto += [
            "",
            _compra_timing("🥇 La mejor", t.mejor, simbolo),
            _compra_timing("🥴 La peor", t.peor, simbolo),
        ]
    texto.append(
        f"\n<i>Comparo lo que pagaste, con comisión, con la media de los "
        f"{t.ventana} días de antes y de después de cada compra. CoinGecko solo "
        "da un año hacia atrás</i>"
    )
    if t.fuera:
        cuantas = "1 compra" if t.fuera == 1 else f"{t.fuera} compras"
        texto.append(
            f"<i>{cuantas} sin lo que costó o sin precios alrededor, fuera</i>"
        )
    return "\n".join(texto)


def _compra_timing(titulo: str, c: "CompraTiming", simbolo: str) -> str:
    m = c.movimiento
    lado = "por debajo" if c.ahorro >= 0 else "por encima"
    return (
        f"{titulo}: {texto_cantidad(m.cantidad)} de {_nombre(m.coin_id)} el "
        f"{m.cuando.astimezone():%d/%m/%Y} a {simbolo}{_num(c.pagado)}, un "
        f"{abs(c.ahorro):.1f}% {lado} de la media ({simbolo}{_num(c.media)})"
    )


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


def formatear_vsbolsa(c: ContraBolsa, currency: str) -> str:
    """Respuesta de /vsbolsa."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        f"📈 <b>Tu cartera contra el {c.indice}</b>",
        f"Lo que compraste vale hoy <b>{simbolo}{_num(c.real)}</b>",
        f"Con ese dinero en un indexado del {c.indice}, en las mismas fechas, "
        f"tendrías {simbolo}{_num(c.bolsa)}",
        "",
    ]
    if abs(c.diferencia) < 0.01 or c.ventaja is None:
        texto.append("🤝 Vas igual que la bolsa")
    else:
        pct = f"{c.ventaja:+.1f}".replace(".", ",")
        diferencia = f"<b>{simbolo}{_num(abs(c.diferencia))}</b> ({pct}%)"
        if c.diferencia > 0:
            texto.append(f"🏆 Le ganas al {c.indice} por {diferencia}")
        else:
            texto.append(f"🐢 El {c.indice} te gana por {diferencia}")
            texto.append("Y con mucho menos susto por el camino.")

    pie = f"Con tus compras y ventas desde el {c.desde.astimezone():%d/%m/%Y}"
    if c.fuera == 1:
        pie += ". 1 movimiento no cuenta: sin precio o sin cierre de bolsa cerca"
    elif c.fuera:
        pie += (
            f". {c.fuera} movimientos no cuentan: sin precio o sin cierre de "
            "bolsa cerca"
        )
    texto += [
        f"<i>{pie}</i>",
        f"<i>Con el ETF {escape(c.ticker)}, que reinvierte los dividendos, al "
        "cierre de cada día y sin comisiones.</i>",
    ]
    return "\n".join(texto)


def formatear_comisiones(c: Comisiones, currency: str, año: int | None) -> str:
    """Respuesta de /comisiones."""
    if not c.con:
        de = f" en {año}" if año else ""
        return (
            f"No tienes ninguna comisión apuntada{de}. Se ponen al final de la "
            "compra o la venta: /compra bitcoin 0.01 600 com 1.5 (o com 0.1%)"
        )
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    de = f" de {año}" if año else ""
    operaciones = "1 operación" if c.con == 1 else f"{c.con} operaciones"
    resumen = f"Has pagado <b>{simbolo}{_num(c.total)}</b> en {operaciones}"
    if c.porcentaje is not None:
        resumen += f", un {c.porcentaje:.2f}% de lo que moviste".replace(".", ",")
    texto = [f"💸 <b>Tus comisiones{de}</b>", "", resumen]

    if len(c.por_año) > 1:
        texto += ["", "📅 <b>Por año</b>"]
        texto += [f"{a}: {simbolo}{_num(t)}" for a, t in c.por_año.items()]
    if len(c.por_cripto) > 1:
        texto += ["", "🪙 <b>Por cripto</b>"]
        texto += [
            f"{escape(coin.replace('-', ' ').title())}: {simbolo}{_num(t)}"
            for coin, t in c.por_cripto.items()
        ]

    if c.sin:
        cuantas = (
            "1 compra o venta no lleva comisión apuntada"
            if c.sin == 1
            else f"{c.sin} compras y ventas no llevan comisión apuntada"
        )
        texto.append(f"\n<i>{cuantas}, o es de antes de guardarla aparte</i>")
    return "\n".join(texto)


def formatear_deposito(c: ContraDeposito, currency: str) -> str:
    """Respuesta de /deposito."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    tipo = _pct(c.tipo)
    en_deposito = f"Ese dinero en un depósito al {tipo}%, en las mismas fechas, sería "
    if c.deposito > 0:
        en_deposito += (
            f"{simbolo}{_num(c.deposito)} ({simbolo}{_num(c.intereses)} de intereses)"
        )
    else:
        en_deposito += "nada: sacaste más de lo que tendría"
    texto = [
        f"🏦 <b>Tu cartera contra un depósito al {tipo}%</b>",
        f"Lo que compraste vale hoy <b>{simbolo}{_num(c.real)}</b>",
        en_deposito,
        "",
    ]

    diferencia = f"<b>{simbolo}{_num(abs(c.diferencia))}</b>"
    if c.ventaja is not None:
        diferencia += f" ({c.ventaja:+.1f}%)".replace(".", ",")
    if abs(c.diferencia) < 0.01:
        texto.append("🤝 Vas igual que el depósito")
    elif c.diferencia > 0:
        texto.append(f"🏆 Le ganas al depósito por {diferencia}")
    else:
        texto.append(f"🐢 El depósito te gana por {diferencia}")

    if c.empate is not None:
        empate = f"{abs(c.empate):,.1f}".replace(",", "@").replace(".", ",")
        empate = empate.replace("@", ".")
        if c.empate > 0:
            texto.append(
                f"📅 Para empatar con tu cartera, el depósito tendría que dar un "
                f"<b>{empate}%</b> al año"
            )
        else:
            texto.append(
                f"📅 Tu cartera pierde un {empate}% al año: cualquier depósito le gana"
            )

    pie = (
        f"Con tus compras y ventas desde el {c.desde.astimezone():%d/%m/%Y}. "
        "Sin impuestos, ni en uno ni en otro"
    )
    if c.fuera == 1:
        pie += ". 1 movimiento no cuenta: sin precio, o venta de lo del .env"
    elif c.fuera:
        pie += (
            f". {c.fuera} movimientos no cuentan: sin precio, o ventas de lo del .env"
        )
    texto.append(f"<i>{pie}</i>")
    return "\n".join(texto)


def formatear_inflacion(i: Inflacion, currency: str) -> str:
    """Respuesta de /inflacion."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    subida = f"{i.subida:.1f}".replace(".", ",")
    texto = [
        "🎈 <b>Tu cartera contra la inflación</b>",
        f"Desde tu primera compra ({i.desde.astimezone():%m/%Y}), los precios en "
        f"España han subido un <b>{subida}%</b>",
        "",
    ]
    if i.necesario > 0:
        texto += [
            f"Pusiste {simbolo}{_num(i.puesto)}: para comprar lo mismo hoy harían "
            f"falta {simbolo}{_num(i.necesario)}",
            f"Lo que te queda vale <b>{simbolo}{_num(i.vale)}</b>",
            "",
        ]
        diferencia = f"{simbolo}{_num(abs(i.diferencia))}"
        de_verdad = f"{abs(i.de_verdad):.1f}".replace(".", ",")
        if abs(i.diferencia) < 0.01:
            texto.append("🤝 Vas justo igual que la inflación")
        elif i.diferencia > 0:
            texto.append(
                f"✅ Le ganas a la inflación: <b>{de_verdad}%</b> más de poder de "
                f"compra ({diferencia} por encima)"
            )
        else:
            texto.append(
                f"🔥 La inflación te gana: has perdido un <b>{de_verdad}%</b> de "
                f"poder de compra ({diferencia} por debajo)"
            )
    else:
        texto.append(
            f"Ya sacaste más de lo que metiste, contando la inflación. Lo que te "
            f"queda, {simbolo}{_num(i.vale)}, es todo ganancia"
        )

    pie = (
        f"Con el IPCA de España de Eurostat, hasta {i.hasta:%m/%Y}, y la fecha de "
        "cada compra y venta"
    )
    if currency.lower() != "eur":
        pie += f". Es la inflación del euro y tu cartera va en {currency.upper()}"
    if i.fuera == 1:
        pie += ". 1 movimiento no cuenta: sin precio, o venta de lo del .env"
    elif i.fuera:
        pie += (
            f". {i.fuera} movimientos no cuentan: sin precio, o ventas de lo del .env"
        )
    texto.append(f"<i>{pie}</i>")
    return "\n".join(texto)


def formatear_pelotazo(p: Pelotazo | None, currency: str) -> str:
    """Respuesta de /pelotazo."""
    if p is None:
        return (
            "No tengo compras con las que comparar. Apúntalas así: "
            "/compra bitcoin 0.01 600"
        )
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = _jugada_pelotazo("🎯 <b>Tu pelotazo", p.mejor, simbolo)
    if p.peor is not None:
        texto += "\n\n" + _jugada_pelotazo("🤦 <b>Tu peor compra", p.peor, simbolo)
    return texto


def _jugada_pelotazo(titulo: str, r: Jugada, simbolo: str) -> str:
    m = r.compra
    nombre = escape(m.coin_id.replace("-", " ").title())
    return (
        f"{titulo}: {nombre} {r.cambio:+.2f}%</b>\n"
        f"{texto_cantidad(m.cantidad)} por {simbolo}{_num(m.coste)} "
        f"el {m.cuando.astimezone():%d/%m/%Y}, hoy valen {simbolo}{_num(r.hoy)}"
    )


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


def formatear_aniversarios(lista: list[Aniversario], currency: str) -> str:
    """El trozo del resumen con las compras que cumplen años hoy."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    if len(lista) == 1:
        texto = ["🎂 <b>Hoy cumple años una de tus compras</b>"]
    else:
        texto = [f"🎂 <b>Hoy cumplen años {len(lista)} de tus compras</b>"]

    for a in lista[:MAX_ANIVERSARIOS]:
        m = a.compra
        nombre = escape(m.coin_id.replace("-", " ").title())
        años = "1 año" if a.años == 1 else f"{a.años} años"
        linea = f"Hace {años} compraste {texto_cantidad(m.cantidad)} de {nombre}"
        if m.coste:
            linea += f" por {simbolo}{_num(m.coste)}"
        if a.valor is not None:
            linea += f": hoy vale <b>{simbolo}{_num(a.valor)}</b>"
            if a.cambio is not None:
                linea += f" {_flecha(a.cambio)} {a.cambio:+.2f}%"
        texto.append(linea)

    if len(lista) > MAX_ANIVERSARIOS:
        texto.append(f"<i>y {len(lista) - MAX_ANIVERSARIOS} más</i>")
    return "\n".join(texto)


def formatear_estable(d: Desvio, vuelve: bool = False) -> str:
    """Aviso de que una estable se ha salido de su dólar, o de que ha vuelto."""
    precio = f"${d.precio:.4f}".replace(".", ",")
    if vuelve:
        return (
            f"✅ <b>{d.simbolo}</b> vuelve a su dólar: está a {precio} "
            f"({d.porcentaje:+.2f}%)"
        )
    return (
        f"⚠️ <b>{d.simbolo} se sale de su dólar</b>\n"
        f"Está a <b>{precio}</b>, un <b>{d.porcentaje:+.2f}%</b>. Una estable "
        "no debería moverse así: mira qué pasa antes de dejar dinero ahí\n"
        "<i>Te aviso otra vez cuando vuelva</i>"
    )


def formatear_volumen(v: Volumen, currency: str) -> str:
    """Aviso de que una que vigilas mueve mucho más volumen de lo normal."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(v.coin_id.replace("-", " ").title())
    veces = f"{v.veces:.1f}".replace(".", ",")
    precio = f"Está a {simbolo}{_num(v.precio)}"
    if v.cambio is not None:
        cambio = f"{v.cambio:+.1f}".replace(".", ",")
        precio += f" ({_flecha(v.cambio)} {cambio}% en 24 h)"
    return (
        f"📢 <b>{nombre} mueve mucho más de lo normal</b>\n"
        f"{simbolo}{grande(v.actual)} negociados en 24 h, {veces} veces lo normal\n"
        f"{precio}\n"
        "<i>Suele haber noticia detrás. No repito hasta que se calme</i>"
    )


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


def formatear_arrepentido(a: Arrepentido, currency: str) -> str:
    """Respuesta de /arrepentido."""
    if not a.vendidas:
        return (
            "No tengo ventas con las que comparar: o no has vendido nada o son de "
            "antes de guardar a cuánto vendías. Las nuevas ya sí: "
            "/venta bitcoin 0.005 350"
        )

    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    lineas = ["🤔 <b>¿Hiciste bien en vender?</b>", ""]
    for v in a.vendidas:
        nombre = escape(v.coin_id.replace("-", " ").title())
        cara = "😩" if v.diferencia > 0 else "😌"
        lineas.append(f"{cara} <b>{nombre}</b>  {_ganancia(v.diferencia, simbolo)}")
        lineas.append(
            f"<i>Vendiste {texto_cantidad(v.cantidad)} por {simbolo}{_num(v.cobrado)}, "
            f"hoy serían {simbolo}{_num(v.hoy)}</i>"
        )

    total = f"{simbolo}{_num(abs(a.total))}"
    if a.total > 0:
        lineas.append(f"\n😩 Si no hubieras vendido, hoy tendrías <b>{total} más</b>")
    else:
        lineas.append(f"\n😌 Bien vendido: hoy te darían <b>{total} menos</b>")
    if a.sin_datos:
        cuantas = "1 venta" if a.sin_datos == 1 else f"{a.sin_datos} ventas"
        lineas.append(f"<i>No cuento {cuantas}: sin lo que te dieron o sin precio.</i>")
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
    lineas.append(f"📄 Venta a venta, para la Renta: /impuestos {i.año} csv")
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


def formatear_modelo721(m: Modelo721, currency: str, hoy: date) -> str:
    """Respuesta de /modelo721."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    limite = f"{simbolo}{_num(LIMITE_721)}"
    dias = "queda 1 día" if m.dias == 1 else f"quedan {m.dias} días"
    lineas = ["🏛️ <b>Modelo 721</b>", ""]

    if m.en_plazo:
        if m.cierre is None:
            lineas.append(
                f"No tengo guardado lo que valía tu cartera el 31/12/{m.año}, así "
                "que no sé si te toca presentar lo de ese año."
            )
        elif m.toca:
            lineas.append(
                f"El 31/12/{m.año} tu cartera valía <b>{simbolo}{_num(m.cierre)}</b>, "
                f"más de {limite}: <b>te toca presentarlo</b>. Tienes hasta el 31 de "
                f"marzo, {dias}."
            )
        else:
            lineas.append(
                f"El 31/12/{m.año} tu cartera valía {simbolo}{_num(m.cierre)}: no "
                f"pasa de {limite}, así que lo de {m.año} no te toca."
            )
        lineas.append("")

    if m.falta < 0:
        lineas.append(
            f"Hoy vale <b>{simbolo}{_num(m.hoy)}</b>. Si el 31 de diciembre sigue "
            f"por encima de {limite}, tendrás que presentarlo en {hoy.year + 1}."
        )
    else:
        lineas.append(
            f"Hoy vale {simbolo}{_num(m.hoy)}: le faltan "
            f"{simbolo}{_num(m.falta)} para pasar de {limite}."
        )

    lineas += [
        "",
        "<i>Solo cuenta lo que tengas en exchanges de fuera de España. Lo de tu "
        "propia wallet o un exchange español no va. Yo miro la cartera entera.</i>",
        f"<i>Si ya lo presentaste, solo vuelve a tocar si sube más de "
        f"{simbolo}{_num(SUBIDA_721)} desde lo que declaraste.</i>",
    ]
    if currency.lower() != "eur":
        lineas.append(
            f"<i>Ojo: va en {currency.upper()}, y el límite es de 50.000 €.</i>"
        )
    return "\n".join(lineas)


def formatear_aviso_renta(i: Impuestos, currency: str, recibido: float) -> str:
    """En abril, lo de /impuestos del año pasado con el plazo."""
    return (
        f"🧾 <b>Ya puedes hacer la Renta de {i.año}</b>\n\n"
        + formatear_impuestos(i, currency, recibido)
        + "\n\n<i>Va en ganancias y pérdidas por transmisión de monedas virtuales. "
        "El plazo suele acabar el 30 de junio.</i>"
    )


def formatear_aviso_721(valor: float, hoy: date) -> str:
    """El aviso de cuando la cartera pasa del límite del 721."""
    return (
        f"🏛️ <b>Tu cartera pasa de €{_num(LIMITE_721)}</b>\n\n"
        f"Vale €{_num(valor)}. Si el 31 de diciembre sigue por encima y la tienes en "
        f"exchanges de fuera, tendrás que presentar el modelo 721 antes del 31 de "
        f"marzo de {hoy.year + 1}.\n\n"
        "<i>Te lo digo una vez al año. Más en /modelo721</i>"
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


def formatear_permuta(p: Permuta, currency: str) -> str:
    """Respuesta de /permuta."""
    s = p.venta
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    origen = escape(s.coin_id.replace("-", " ").title())
    destino = escape(p.destino.replace("-", " ").title())
    lineas = [
        f"🔁 <b>Si cambias {texto_cantidad(s.vendido)} de {origen} por {destino}</b>",
        "",
        f"Te darían <b>{texto_cantidad(p.recibes)}</b> de {destino}  "
        f"<i>(a {simbolo}{_num(p.precio_destino)} cada una)</i>",
        f"Valen {simbolo}{_num(p.valor)}{_con_comision(p.comision, simbolo)}",
    ]

    if s.ganancia is None:
        lineas.append(
            f"No sé lo que te costó el {origen}, así que no puedo sacar lo que "
            "le tocaría a Hacienda."
        )
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
        if s.ganancia > 0:
            lineas.append(
                "Aunque no veas un euro: cambiar una cripto por otra cuenta como "
                "venderla."
            )

    lineas.append(
        f"El {destino} contará como comprado a {simbolo}{_num(p.valor)}: es lo que "
        "restarás cuando lo vendas."
    )
    if s.queda:
        lineas.append(f"Te quedarían {texto_cantidad(s.queda)} de {origen}")

    if s.sin_datos:
        cuantas = "1 venta" if s.sin_datos == 1 else f"{s.sin_datos} ventas"
        lineas.append(f"<i>No cuento {cuantas} de este año: les falta el precio.</i>")
    if currency.lower() != "eur":
        lineas.append(
            f"<i>Ojo: va en {currency.upper()}, y Hacienda lo quiere en euros.</i>"
        )
    lineas.append(
        "\n<i>No apunto nada. Es orientativo, con FIFO y al precio de ahora.</i>"
    )
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


def formatear_importacion(
    nuevas: list[Operacion],
    saltadas: dict[str, int],
    sin_comision: int,
    repetidas: int,
    viejas: int,
    ultimo: datetime | None,
    currency: str,
    origen: str = "Binance",
) -> str:
    """Lo que hay en el CSV antes de apuntarlo, para que digas sí o no."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [f"📥 <b>Lo que he leído del CSV de {origen}</b>"]
    if nuevas:
        compras = [o for o in nuevas if o.tipo == "compra"]
        ventas = [o for o in nuevas if o.tipo == "venta"]
        criptos = sorted({o.coin_id for o in nuevas})
        texto.append(f"🟢 {len(compras)} compras · 🔴 {len(ventas)} ventas")
        texto.append(", ".join(_nombre(c) for c in criptos))
        texto.append(f"Del {nuevas[0].cuando:%d/%m/%Y} al {nuevas[-1].cuando:%d/%m/%Y}")
        texto.append(
            f"Metiste {simbolo}{_num(sum(o.coste for o in compras))}"
            f" y sacaste {simbolo}{_num(sum(o.coste for o in ventas))}"
        )
    else:
        texto.append("No hay nada nuevo que apuntar.")

    notas = []
    if repetidas:
        notas.append(f"{repetidas} ya estaban apuntadas, no las repito")
    if viejas:
        # FIFO y Hacienda van por orden de apunte: meterlas detrás las liaría
        notas.append(
            f"{viejas} son de antes de tu último movimiento "
            f"({ultimo:%d/%m/%Y}) y no las meto: desordenarían las cuentas"
        )
    for motivo, cuantas in saltadas.items():
        notas.append(f"{cuantas} saltadas: {escape(motivo)}")
    if sin_comision:
        notas.append(f"{sin_comision} pagaron la comisión en BNB, van sin ella")
    if notas:
        texto.append("")
        texto.extend(f"• {n}" for n in notas)

    if nuevas:
        texto.append(
            "\n⚠️ Se suman a lo que ya tienes. Si ya estaban en tu PORTFOLIO "
            "o las apuntaste con /compra, contarían dos veces."
        )
    return "\n".join(texto)


def formatear_importada(apuntadas: int, fallidas: int, origen: str = "Binance") -> str:
    """Respuesta al pulsar Importar."""
    texto = [
        f"✅ Apuntadas {apuntadas} operaciones de {origen}. Míralas en /movimientos"
    ]
    if fallidas:
        texto.append(
            f"⚠️ {fallidas} {'ventas' if fallidas > 1 else 'venta'} sin apuntar: "
            "vendías más de lo que tenías apuntado"
        )
    return "\n".join(texto)


BINANCE_SIN_CLAVE = (
    "🏦 <b>Binance contra lo apuntado</b>\n"
    "Para mirarlo necesito una clave de solo lectura:\n"
    "1. En Binance: Perfil → Gestión de API → Crear API\n"
    "2. Déjale solo <b>Habilitar lectura</b>. Nada de trading ni retiradas\n"
    "3. Pon la clave y el secreto en el .env, en BINANCE_API_KEY y "
    "BINANCE_API_SECRET, y reinicia el bot"
)


def formatear_binance(c: Comparacion) -> str:
    """Respuesta de /binance."""
    if not c.diferencias and not c.desconocidas:
        return "No tienes nada en Binance ni apuntado en la cartera."

    lineas = ["🏦 <b>Binance contra lo apuntado</b>", ""]
    cuadran = [d for d in c.diferencias if d.cuadra]
    for d in c.diferencias:
        if d.cuadra:
            continue
        nombre = f"<b>{_nombre(d.coin_id)}</b>"
        if not d.apuntado:
            lineas.append(
                f"➕ {nombre}: {texto_cantidad(d.en_binance)} en Binance, sin apuntar"
            )
        elif not d.en_binance:
            lineas.append(
                f"➖ {nombre}: {texto_cantidad(d.apuntado)} apuntado, nada en Binance"
            )
        else:
            mas = "más" if d.falta > 0 else "menos"
            lineas.append(
                f"↔️ {nombre}: {texto_cantidad(d.en_binance)} en Binance, "
                f"{texto_cantidad(d.apuntado)} apuntado "
                f"({texto_cantidad(abs(d.falta))} {mas} en Binance)"
            )
    if cuadran:
        if len(lineas) > 2:
            lineas.append("")
        nombres = ", ".join(_nombre(d.coin_id) for d in cuadran)
        lineas.append(f"✅ Cuadran: {nombres}")
    if c.desconocidas:
        lineas.append(f"❓ No sé qué es: {', '.join(c.desconocidas)}")
    lineas.append(
        "\n<i>Lo de menos en Binance puede estar en otro sitio. Solo miro el "
        "spot y Simple Earn flexible: futuros o staking bloqueado no salen. "
        "Lo que falte se apunta con /compra o /venta.</i>"
    )
    return "\n".join(lineas)
