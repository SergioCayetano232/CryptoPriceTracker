"""Precios, máximos y cómo va el mercado."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from ..altseason import ALTCOINS, BITCOIN, CUANTAS, DIAS, Moneda, Temporada
from ..avisados import Ultimo
from ..aviso_tendencias import Nueva
from ..cartera import Valor
from ..comisionred import TAMAÑO as TAMAÑO_ENVIO
from ..comisionred import ComisionRed, en_dinero, media_hora
from ..comparar import Resultado
from ..comparar import media as media_comparar
from ..copia import numero as numero_env
from ..mapa import Mapa
from ..maximo import Maximo, hace
from ..mercado import Mercado, grande
from ..miedo import NOMBRES as NOMBRES_MIEDO
from ..miedo import Indice
from ..miedo import hace as dia_miedo
from ..miedo import nombre as nombre_miedo
from ..movimientos import texto_cantidad
from ..periodo import nombre as nombre_periodo
from ..quieta import Quieta
from ..semanal import Semana
from ..sesgo import MINIMO as MINIMO_SESGO
from ..sesgo import Lado, Sesgo
from ..telegram import escape
from ..tendencias import Tendencia
from ..top import ENTRE, Movida
from .base import (
    BARRAS_MOVIL,
    MINIMO_BARRAS,
    SIMBOLOS,
    _barra_progreso,
    _es,
    _flecha,
    _ganancia,
    _nombre,
    _num,
    _peso,
    _signo,
    describir,
    muestrear,
    sparkline,
)

# Solo para el tipo: esos módulos importan de alerts y se haría un círculo.
if TYPE_CHECKING:
    from ..ruido import Ruido
    from ..voto import Votos


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


def formatear_tendencias(lista: list[Tendencia], avisando: bool = True) -> str:
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
    if not avisando:
        texto.append(
            "<i>Para que te avise si sale una de las tuyas: /tendencias avisa</i>"
        )
    return "\n".join(texto)


def formatear_aviso_tendencias(lista: list[Nueva]) -> str:
    """Cuando algo tuyo entra en lo que más se busca."""
    lineas = []
    for n in lista:
        t = n.tendencia
        linea = f"{n.lugar}. <b>{escape(t.nombre)}</b>"
        if t.variacion is not None:
            linea += f"  {_flecha(t.variacion)} {t.variacion:+.2f}% en 24 h"
        lineas.append(linea)
    if len(lista) == 1:
        titulo = f"🔥 <b>{escape(lista[0].tendencia.nombre)} está de moda</b>"
    else:
        titulo = f"🔥 <b>{len(lista)} de las tuyas están de moda</b>"
    return (
        f"{titulo}\nEn lo que más se busca hoy en CoinGecko:\n\n"
        + "\n".join(lineas)
        + "\n\n<i>Que se hable de una no dice si va a subir: a veces el ruido "
        "llega cuando ya ha subido. La lista entera, en /tendencias</i>"
    )


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


def formatear_altseason(t: Temporada, mias: list[str]) -> str:
    """/altseason. mias, las que vigilas, por si alguna está entre las grandes."""
    if t.toca == "altcoins":
        lectura = "🌈 <b>Temporada de altcoins</b>: casi todas le ganan a bitcoin"
    elif t.toca == "bitcoin":
        lectura = "🟠 <b>Temporada de bitcoin</b>: casi ninguna le gana"
    else:
        lectura = "⚖️ <b>Ni de altcoins ni de bitcoin</b>: unas sí y otras no"

    def lista(monedas: list[Moneda]) -> str:
        return " · ".join(f"{escape(m.simbolo)} {_signo(m.cambio)}" for m in monedas)

    gana = "le gana" if len(t.ganan) == 1 else "le ganan"
    texto = [
        f"🌈 <b>Índice de altseason: {t.indice}</b>",
        _barra_progreso(t.indice),
        f"{len(t.ganan)} de {len(t.monedas)} {gana} a bitcoin en {DIAS} días, "
        f"que lleva {_signo(t.bitcoin)}.",
        "",
        lectura,
        "",
        f"🔺 Las que más: {lista(t.mejores())}",
        f"🔻 Las que menos: {lista(t.peores())}",
    ]
    tuyas = [m for m in t.monedas if m.coin_id in mias]
    if tuyas:
        texto.append(
            "👀 De las tuyas: "
            + " · ".join(
                f"{escape(m.simbolo)} {_signo(m.cambio)} "
                f"{'✅' if m.cambio > t.bitcoin else '❌'}"
                for m in tuyas
            )
        )
    texto += [
        "",
        f"<i>Con {ALTCOINS} o más es temporada de altcoins y con {BITCOIN} o menos, "
        f"de bitcoin. Cuento las {CUANTAS} más grandes sin estables ni copias de "
        "otras. Hacia dónde va el dinero: /dominancia</i>",
    ]
    return "\n".join(texto)


def formatear_mapa(m: Mapa) -> str:
    """El pie de /mapa, y lo que se manda si la imagen no sale."""
    mas = max(m.casillas, key=lambda c: c.variacion)
    menos = min(m.casillas, key=lambda c: c.variacion)
    suben = f"{m.suben} {'sube' if m.suben == 1 else 'suben'}"
    bajan = f"{m.bajan} {'baja' if m.bajan == 1 else 'bajan'}"
    texto = [
        f"🗺 <b>El mercado en 24 h: {_signo(m.media)}</b>",
        f"De las {len(m.casillas)} más grandes, 🔺 {suben} y 🔻 {bajan}.",
    ]
    if mas.variacion > 0:
        texto.append(f"La que más sube: {escape(mas.simbolo)} {_signo(mas.variacion)}")
    if menos.variacion < 0:
        texto.append(
            f"La que más baja: {escape(menos.simbolo)} {_signo(menos.variacion)}"
        )
    texto.append(
        "<i>El total pesa cada una por lo que vale: si bitcoin cae, se nota más.</i>"
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


def _cuesta_envio(sats: int, precio_btc: float | None, simbolo: str) -> str:
    if not precio_btc:
        return f"{_es(f'{sats:,}')} sats"
    dinero = en_dinero(sats, precio_btc)
    if dinero < 0.01:
        return f"menos de 1 céntimo ({sats} sats)"
    return f"{simbolo}{_es(f'{dinero:,.2f}')}"


def formatear_aviso_comisionred(
    c: ComisionRed, limite: int, precio_btc: float | None, currency: str
) -> str:
    """El aviso de /comisionred 5, cuando la red baja a lo que pediste."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    t = media_hora(c.tarifas)
    return "\n".join(
        [
            "⛓️ <b>Mover bitcoin ya está barato</b>",
            f"{t.emoji} {t.nombre}: <b>{_cuesta_envio(t.sats, precio_btc, simbolo)}"
            f"</b> · {t.sats_vb} sat/vB",
            f"Pedías {limite} o menos. Buen momento para pasarlo a tu monedero.",
            "<i>Con prisa y sin ella, en /comisionred. Era un aviso de una vez: "
            f"para otro, /comisionred {limite}</i>",
        ]
    )


def formatear_comisionred(
    c: ComisionRed | None,
    precio_btc: float | None,
    currency: str,
    aviso: int | None = None,
) -> str:
    """Respuesta de /comisionred. Sin precio de bitcoin, solo en sats.

    aviso es a cuántos sat/vB tienes puesto que te avise, si lo tienes.
    """
    if c is None:
        return "mempool.space no me ha dado las comisiones. Prueba en un rato."
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")

    def cuesta(sats: int) -> str:
        return _cuesta_envio(sats, precio_btc, simbolo)

    texto = ["⛓️ <b>Lo que cuesta mover bitcoin ahora</b>", ""]
    for t in c.tarifas:
        texto.append(
            f"{t.emoji} {t.nombre}: <b>{cuesta(t.sats)}</b> · {t.sats_vb} sat/vB"
        )

    normal = f"{c.semana:g}".replace(".", ",") if c.semana else ""
    veredicto = {
        "regalada": "🎁 Casi regalada: da igual cuándo lo hagas",
        "barata": f"🟢 Barata: lo normal esta semana es {normal} sat/vB. "
        "Buen momento para pasarlo a tu monedero",
        "normal": f"🟡 Normal para esta semana ({normal} sat/vB)",
        "cara": f"🔴 Cara: lo normal esta semana es {normal} sat/vB. "
        "Si no corre prisa, espera",
    }.get(c.nivel)
    if veredicto:
        texto += ["", veredicto]
    if aviso is not None:
        texto += [
            "",
            f"🔔 Te aviso cuando la de media hora baje a {aviso} sat/vB. "
            "Para quitarlo: /comisionred no",
        ]

    texto += [
        "",
        f"<i>Un envío normal, de una entrada y dos salidas ({TAMAÑO_ENVIO} vB). "
        "Si juntas muchas entradas pequeñas, sale más caro. Datos de "
        '<a href="https://mempool.space">mempool.space</a></i>',
    ]
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


# Lo que se dice según el índice medio de los días en que compras o vendes.
HUMOR_COMPRAS = {
    "miedo": "Compras sobre todo con miedo: entras cuando los demás huyen, que suele "
    "salir mejor",
    "codicia": "Compras sobre todo con codicia: sueles entrar cuando ya ha subido y "
    "todo el mundo está contento",
    "neutral": "Ni con miedo ni con codicia: compras sin dejarte llevar mucho",
}
HUMOR_VENTAS = {
    "miedo": "Vendes sobre todo con miedo: ojo, suele ser vender en pleno pánico, "
    "cerca del suelo",
    "codicia": "Vendes sobre todo con codicia: recoges cuando todos están eufóricos, "
    "que suele salir bien",
    "neutral": "Vendes sin dejarte llevar por el humor del mercado",
}


def formatear_sesgo(s: Sesgo) -> str:
    """/sesgo: el índice de miedo de los días en que compras y vendes."""
    texto = ["🧠 <b>Con qué humor del mercado compras y vendes</b>"]
    for titulo, lado, humores in (
        ("Compras", s.compras, HUMOR_COMPRAS),
        ("Ventas", s.ventas, HUMOR_VENTAS),
    ):
        if lado is not None:
            texto += ["", *_lado_sesgo(titulo, lado, humores)]

    texto.append(
        "\n<i>El índice es el de alternative.me del día de cada movimiento (0 pánico, "
        "100 euforia). Lo de «hoy» es lo que valen esas compras ahora contra lo que "
        "pagaste</i>"
    )
    if s.sin_indice:
        cuantos = "1 movimiento" if s.sin_indice == 1 else f"{s.sin_indice} movimientos"
        texto.append(f"<i>{cuantos} sin índice de ese día, fuera de la cuenta</i>")
    return "\n".join(texto)


def _lado_sesgo(titulo: str, lado: Lado, humores: dict[str, str]) -> list[str]:
    lineas = [f"<b>{titulo}</b> ({lado.veces}) · índice medio {lado.media:.0f}"]
    for g in lado.grupos:
        emoji, nombre = NOMBRES_MIEDO[g.clase]
        linea = f"{emoji} {nombre}: {g.veces}"
        if g.cambio is not None:
            linea += f" · hoy {_flecha(g.cambio)} {g.cambio:+.1f}%"
        lineas.append(linea)
    if lado.humor is None:
        lineas.append(
            f"<i>Con menos de {MINIMO_SESGO} no me atrevo a decir que es costumbre</i>"
        )
    else:
        lineas.append(f"👉 {humores[lado.humor]}")
    return lineas


def formatear_voto(coin_id: str, util: bool, v: "Votos") -> str:
    """Lo que contesta el botón 👍 o 👎 de un aviso. v, los de los últimos 30 días."""
    nombre = _nombre(coin_id)
    if util:
        texto = f"👍 Apuntado: el aviso de <b>{nombre}</b> te sirvió."
    else:
        texto = f"👎 Apuntado: el aviso de <b>{nombre}</b> sobraba."
    texto += f"\nEn 30 días llevas 👍 {v.utiles} · 👎 {v.sobran}."
    if v.muchos_sobran:
        texto += f" Te sobran la mayoría: mira una regla mejor en /ruido {coin_id}"
    return texto


def formatear_ruido(
    lista: "list[Ruido]", horas: float, currency: str, desde: datetime | None
) -> str:
    """/ruido: cuántos avisos de /vigilar se dieron la vuelta en un día."""
    texto = [f"🔊 <b>Avisos en falso</b> · <i>{nombre_periodo(horas)}</i>"]
    for r in lista:
        c = r.cuenta
        como = describir(r.watch, currency)
        texto += ["", f"<b>{_nombre(r.watch.coin_id)}</b>  {como}"]
        v = r.votos
        tuyos = f"Tus votos: 👍 {v.utiles} · 👎 {v.sobran}" if v.total else ""
        if not c.avisos:
            texto.append("Ningún aviso en el tramo")
            if tuyos:
                texto.append(tuyos)
            continue

        avisos = "1 aviso" if c.avisos == 1 else f"{c.avisos} avisos"
        if not c.cerrados:
            texto.append(f"{avisos}, todavía sin 24 h detrás para saber")
            if tuyos:
                texto.append(tuyos)
            continue
        if c.falsos:
            linea = f"{avisos}, <b>{c.falsos} en falso</b> ({c.proporcion:.0%})"
        else:
            linea = f"{avisos}, ninguno en falso"
        icono = "🔴" if c.mucho else "🟢" if not c.falsos else "🟡"
        texto.append(f"{icono} {linea}")
        if c.pendientes:
            texto.append(f"<i>Más {c.pendientes} de las últimas 24 h, aún por ver</i>")
        if tuyos:
            texto.append(tuyos)

        if r.propuesta:
            otra, suya = r.propuesta
            if otra.percent is not None:
                regla = f"%{numero_env(otra.percent)}"
            else:
                regla = numero_env(otra.step)
            cuantos = "1 aviso" if suya.avisos == 1 else f"{suya.avisos} avisos"
            falsos = "ninguno" if not suya.falsos else str(suya.falsos)
            # Si el precio no veía ruido, la propuesta sale de tus 👎.
            if not c.mucho:
                texto.append("Te sobran la mayoría, así que pruebo una más ancha")
            texto.append(
                f"👉 Con {regla}: {cuantos}, {falsos} en falso · "
                f"<code>/vigilar {escape(otra.coin_id)} {regla}</code>"
            )
        elif c.mucho:
            texto.append("Ni abriendo la regla se le quita el ruido")

    texto.append(
        "\n<i>En falso es que en 24 h lo deshizo: volvió a cruzar el precio, o en "
        "los de % deshizo la mitad de lo que se movió. Es con tus reglas de hoy "
        "sobre los precios guardados; no cuenta /alerta ni los avisos automáticos. "
        "Tus votos son los 👍 y 👎 de debajo de cada aviso</i>"
    )
    if desde:
        texto.append(f"<i>Solo tengo precios desde el {desde.astimezone():%d/%m}</i>")
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
