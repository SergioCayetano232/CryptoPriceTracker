"""Los mensajes de los indicadores y del análisis de precios."""

import math
from datetime import date, datetime

from ..backtest import INICIAL as INICIAL_BACKTEST
from ..backtest import Backtest
from ..bollinger import PERIODO as PERIODO_BOLLINGER
from ..bollinger import Bandas
from ..caida import Caida
from ..correlacion import Correlacion, Matriz
from ..cuando import Cuando
from ..diames import POCOS_MESES as POCOS_MESES_DIAMES
from ..diames import DiasMes
from ..diasemana import DiasSemana
from ..direccion import EJEMPLO as EJEMPLO_DIRECCION
from ..direccion import Saldo, Vigilada, a_moneda, coin_id, es_eth, ver
from ..doble import Cartera as CarteraDoble
from ..dominancia import Dominancia
from ..equilibrio import Cartera, Equilibrio
from ..estacional import MESES as MESES_ESTACIONAL
from ..estacional import POCOS_AÑOS, Estacional
from ..estocastico import ALTO as ALTO_ESTOCASTICO
from ..estocastico import BAJO as BAJO_ESTOCASTICO
from ..estocastico import PERIODO as PERIODO_ESTOCASTICO
from ..estocastico import Estocastico
from ..fibonacci import Fibonacci
from ..funding import Funding
from ..futuro import Futuro
from ..horas import Horas
from ..longshort import LongShort
from ..longshort import lectura as lectura_longshort
from ..macd import LENTA, RAPIDA, Macd
from ..macd import SEÑAL as SEÑAL_MACD
from ..maximo import hace
from ..mayer import BURBUJA, Mayer
from ..media import lado_de_todas
from ..mejor import Extremo
from ..mercado import grande
from ..mes import MESES as NOMBRES_MESES
from ..mitad import Cartera as CarteraMitad
from ..movimientos import texto_cantidad
from ..oi import Interes, lectura
from ..perdido import Perdido
from ..periodo import nombre as nombre_periodo
from ..premium import Premium
from ..profundidad import Profundidad
from ..puntuales import CARTERA
from ..racha import Racha
from ..rango import Rango, barra
from ..ratio import Ratio
from ..rebalanceo import EJEMPLO as EJEMPLO_REBALANCEO
from ..rebalanceo import Paso
from ..reparto import OTRAS, Trozo, demasiado
from ..rsi import PERIODO, SOBRECOMPRA, SOBREVENTA, Rsi, hasta_zona
from ..semaforo import AMBAR, VERDE, Voto
from ..sharpe import Sharpe
from ..soporte import Nivel, Soportes
from ..sube import Subida
from ..tarjeta import Tarjeta
from ..telegram import escape
from ..verdes import Verdes
from .base import (
    BARRAS_MOVIL,
    MINIMO_BARRAS,
    POR_BTC,
    SIMBOLOS,
    _barra_progreso,
    _decimal,
    _flecha,
    _nombre,
    _num,
    _pct,
    _signo,
    _veces,
    muestrear,
    sparkline,
)


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


def formatear_correlaciones(m: Matriz, horas: float) -> str:
    """Pie de /correlacion todas: lo que hay que mirar de la imagen."""
    pares = m.con_valor

    def par(a: str, b: str, v: float) -> str:
        valor = f"{v:+.2f}".replace(".", ",")
        return f"{_nombre(a)} y {_nombre(b)} ({valor})"

    lineas = [f"🔗 <b>Cómo se mueven juntas</b>, {nombre_periodo(horas)}", ""]
    lineas.append(f"Las que más: {par(*pares[0])}")
    if len(pares) > 1:
        lineas.append(f"Las que menos: {par(*pares[-1])}")
    media = m.media
    if media >= 0.7:
        como = "se mueven casi como una sola, tenerlas todas reparte poco el riesgo"
    elif media >= 0.4:
        como = "suelen ir juntas"
    else:
        como = "van bastante por libre"
    lineas += ["", f"De media {f'{media:+.2f}'.replace('.', ',')}: {como}"]

    medidas = {c for a, b, _ in pares for c in (a, b)}
    sin_datos = [c for c in m.ids if c not in medidas]
    if sin_datos:
        nombres = ", ".join(_nombre(c) for c in sin_datos)
        lineas.append(f"<i>Sin días suficientes para comparar: {nombres}</i>")
    return "\n".join(lineas)


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


# Con más, el mensaje ya no se lee de un vistazo, que es la idea.
MAX_PERDIDO = 8


def formatear_perdido(p: Perdido, currency: str, cuanto: str) -> str:
    """Lo que ha pasado mientras callaba. cuanto es el tiempo ya en texto."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    lineas = [f"👀 <b>Mientras callaba</b> ({cuanto})", ""]
    if not p.movidas:
        lineas.append("No guardé precios mientras callaba.")
    for m in p.movidas[:MAX_PERDIDO]:
        lineas.append(
            f"{_flecha(m.cambio)} <b>{_nombre(m.coin_id)}</b> {_signo(m.cambio)}: "
            f"de {simbolo}{_num(m.antes)} a {simbolo}{_num(m.ahora)} "
            f"<i>(entre {simbolo}{_num(m.minimo)} y {simbolo}{_num(m.maximo)})</i>"
        )
    if len(p.movidas) > MAX_PERDIDO:
        lineas.append(
            f"<i>y {len(p.movidas) - MAX_PERDIDO} más, que se movieron menos</i>"
        )
    if p.cartera is not None:
        lineas += ["", f"💼 Tu cartera: {_signo(p.cartera)}"]
    return "\n".join(lineas)


def formatear_tarjeta(t: Tarjeta) -> str:
    """El pie de /tarjeta, y lo que va solo si la imagen no sale."""
    lineas = ["🪪 <b>Tu tarjeta</b>, lista para reenviar"]
    if t.total is not None:
        lineas.append(f"{_signo(t.total)} sobre lo que has metido")
    if t.tramo is not None:
        lineas.append(f"{_signo(t.tramo)} en los {nombre_periodo(t.horas)}")
    if t.reparto:
        lineas.append(
            " · ".join(
                f"{'Otras' if r.coin_id == OTRAS else _nombre(r.coin_id)} {r.peso:.0f}%"
                for r in t.reparto
            )
        )
    lineas.append("<i>Solo lleva porcentajes: nadie ve cuánto tienes.</i>")
    return "\n".join(lineas)


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


def formatear_fibonacci(
    coin_id: str,
    f: Fibonacci,
    horas: float,
    currency: str,
    desde: datetime | None = None,
) -> str:
    """Respuesta de /fibonacci. desde va si no hay precios de todo el tramo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    r = f.rango

    def pct(valor: float) -> str:
        return f"{valor:.1f}".replace(".", ",").removesuffix(",0") + "%"

    def precio(valor: float) -> str:
        return f"{simbolo}{_num(valor)}"

    alto = f"{precio(r.maximo)} ({r.cuando_maximo.astimezone():%d/%m})"
    bajo = f"{precio(r.minimo)} ({r.cuando_minimo.astimezone():%d/%m})"
    if f.subiendo:
        que = f"Subió de {bajo} a {alto}: hasta dónde podría corregir"
    else:
        que = f"Bajó de {alto} a {bajo}: hasta dónde podría rebotar"
    texto = [
        f"🌀 <b>{nombre}</b>: Fibonacci, {nombre_periodo(horas)}",
        que,
        "",
    ]

    puesto = False
    for n in f.niveles:
        if not puesto and n.precio < f.ahora:
            texto.append(f"👉 <b>Ahora {precio(f.ahora)}</b>")
            puesto = True
        extremo = ""
        if n.pct == 0:
            extremo = " · el máximo" if f.subiendo else " · el mínimo"
        elif n.pct == 100:
            extremo = " · el mínimo" if f.subiendo else " · el máximo"
        texto.append(f"{pct(n.pct)}: {precio(n.precio)}{extremo}")
    if not puesto:
        texto.append(f"👉 <b>Ahora {precio(f.ahora)}</b>")

    def nombre_nivel(n) -> str:
        if n.pct in (0, 100):
            return "el máximo" if n.precio == r.maximo else "el mínimo"
        return f"el {pct(n.pct)}"

    texto.append("")
    for emoji, donde, n in (
        ("🛟", "Por debajo", f.debajo),
        ("🧱", "Por encima", f.encima),
    ):
        if n:
            a = f"{(n.precio / f.ahora - 1) * 100:+.1f}".replace(".", ",")
            texto.append(
                f"{emoji} {donde}, {nombre_nivel(n)} ({precio(n.precio)}), a un {a}%"
            )
    texto.append(
        "<i>Los niveles entre el máximo y el mínimo donde muchos esperan que "
        "frene el precio, y por eso a veces frena. El que más se mira es el "
        "61,8%. Sale de lo guardado</i>"
    )
    if desde is not None:
        texto.append(f"<i>Solo tengo precios desde el {desde.astimezone():%d/%m}</i>")
    return "\n".join(texto)


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


def formatear_backtest(
    coin_id: str,
    b: Backtest,
    horas: float,
    currency: str,
    desde: datetime | None = None,
) -> str:
    """Respuesta de /backtest. desde va si no hay precios de todo el tramo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = _nombre(coin_id)
    pct = _pct(b.porcentaje)
    operaciones = (
        f"{_veces(b.ventas, 'venta', 'ventas')} y "
        f"{_veces(b.compras, 'compra', 'compras')}"
    )
    lineas = [
        f"🧪 <b>{nombre}: vender al +{pct}% y recomprar al -{pct}%</b>",
        f"<i>{nombre_periodo(horas).capitalize()}, empezando con "
        f"{simbolo}{_num(INICIAL_BACKTEST)} el {b.desde.astimezone():%d/%m/%Y}</i>",
        "",
        f"Con la regla: <b>{simbolo}{_num(b.final)}</b> ({_signo(b.regla)}), "
        f"{operaciones}",
        f"Sin tocar nada: {simbolo}{_num(b.hodl)} ({_signo(b.sin_tocar)})",
        "",
    ]
    if not b.ventas:
        lineas.append(f"🤝 Nunca subió un {pct}%: no habrías hecho nada.")
    elif abs(b.diferencia) < 0.01:
        lineas.append("🤝 Te quedas igual que sin tocar nada.")
    elif b.diferencia > 0:
        lineas.append(f"🏆 La regla gana por <b>{simbolo}{_num(b.diferencia)}</b>")
    else:
        lineas.append(
            f"🐢 No tocar nada gana por <b>{simbolo}{_num(-b.diferencia)}</b>"
        )

    if b.dentro:
        lineas.append(
            f"Ahora tendrías {nombre}: venderías si sube a {simbolo}{_num(b.siguiente)}"
        )
    else:
        lineas.append(
            f"Ahora estarías fuera: recomprarías si baja a {simbolo}{_num(b.siguiente)}"
        )

    if desde is not None:
        lineas.append(
            f"\n<i>Solo tengo precios desde el {desde.astimezone():%d/%m/%Y}. "
            "/rellenar baja los que faltan.</i>"
        )
    lineas.append(
        "\n<i>Con los precios que tengo guardados, sin comisiones ni impuestos: "
        "cada venta con ganancia paga a Hacienda. Que haya salido bien antes no "
        "quiere decir que vaya a salir bien después.</i>"
    )
    return "\n".join(lineas)


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


def _saldo(
    direccion: str, unidades: int, precios: dict[str, float], currency: str
) -> str:
    """'0,05 BTC (€3.200,00)' o '1,5 ETH (...)'. Sin precio, solo la cantidad."""
    cantidad = a_moneda(direccion, abs(unidades))
    sigla = "ETH" if es_eth(direccion) else "BTC"
    texto = f"{cantidad:.8f}".rstrip("0").rstrip(".").replace(".", ",")
    precio = precios.get(coin_id(direccion))
    if not precio:
        return f"{texto} {sigla}"
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    return f"{texto} {sigla} ({simbolo}{_num(cantidad * precio)})"


def _corta(direccion: str) -> str:
    return f"{direccion[:6]}…{direccion[-4:]}"


def formatear_direcciones(
    lista: list[Vigilada], precios: dict[str, float], currency: str
) -> str:
    """/direccion a secas."""
    if not lista:
        return (
            "No vigilo ninguna dirección. Añade una así: "
            f"<code>{escape(EJEMPLO_DIRECCION)}</code>"
        )
    texto = ["👀 <b>Las direcciones que vigilo</b>", ""]
    for v in lista:
        saldo = _saldo(v.direccion, v.sats, precios, currency)
        texto.append(
            f"• <b>{escape(v.nombre)}</b>: {saldo} · "
            f'<a href="{ver(v.direccion)[0]}">{_corta(v.direccion)}</a>'
        )
    # BTC y ETH no se suman: cada red con su total.
    for red in (False, True):
        de_esta = [v for v in lista if es_eth(v.direccion) is red]
        if len(de_esta) > 1:
            total = sum(v.sats for v in de_esta)
            una = de_esta[0].direccion
            texto += [
                "",
                f"Entre todas: <b>{_saldo(una, total, precios, currency)}</b>",
            ]
    # En ethereum el nodo da el saldo ya confirmado; tarda unos 12 segundos más.
    sin_confirmar = (
        " En bitcoin, sin esperar a que se confirme."
        if any(not es_eth(v.direccion) for v in lista)
        else ""
    )
    texto += [
        "",
        f"<i>Te aviso en cuanto entre o salga algo.{sin_confirmar} "
        "Para dejar de vigilar una: /direccion quitar nombre</i>",
    ]
    return "\n".join(texto)


def formatear_direccion_nueva(
    v: Vigilada, precios: dict[str, float], currency: str
) -> str:
    return (
        f"👀 Vigilo <b>{escape(v.nombre)}</b>: ahora tiene "
        f"{_saldo(v.direccion, v.sats, precios, currency)}. Te aviso en cuanto se mueva"
    )


def formatear_movimiento_direccion(
    v: Vigilada, cambio: int, ahora: Saldo, precios: dict[str, float], currency: str
) -> str:
    """El aviso de cuando una de /direccion se mueve. v es como estaba antes."""
    texto = [f"🔔 <b>Se ha movido {escape(v.nombre)}</b>"]
    if cambio > 0:
        cuanto = _saldo(v.direccion, cambio, precios, currency)
        texto.append(f"📥 Han entrado <b>{cuanto}</b>")
    elif cambio < 0:
        cuanto = _saldo(v.direccion, cambio, precios, currency)
        texto.append(f"📤 Han salido <b>{cuanto}</b>")
    else:
        texto.append("Ha tenido movimiento, pero el saldo sigue igual")
    enlace, web = ver(v.direccion)
    texto += [
        f"Ahora tiene {_saldo(v.direccion, ahora.sats, precios, currency)}",
        "",
        f'<a href="{enlace}">Verlo en {web}</a>',
    ]
    return "\n".join(texto)


def formatear_estacional(coin_id: str, e: Estacional, hoy: date | None = None) -> str:
    """Respuesta de /estacional."""
    nombre = escape(coin_id.replace("-", " ").title())
    este = (hoy or date.today()).month

    def pct(valor: float) -> str:
        return f"{valor:+.1f}%".replace(".", ",")

    texto = [f"📅 <b>{nombre}</b> mes a mes, desde {e.desde}", ""]
    for m in e.meses:
        marca = " ← este mes" if m.mes == este else ""
        texto.append(
            f"{_flecha(m.suele)} {MESES_ESTACIONAL[m.mes - 1][:3].title()}: "
            f"<b>{pct(m.suele)}</b> · subió {m.subio} de {m.veces}{marca}"
        )

    mejor, peor = e.mejor, e.peor
    if len(e.meses) > 1:
        texto += [
            "",
            f"🏆 El mejor, <b>{MESES_ESTACIONAL[mejor.mes - 1]}</b> "
            f"({pct(mejor.suele)})",
            f"💀 El peor, <b>{MESES_ESTACIONAL[peor.mes - 1]}</b> ({pct(peor.suele)})",
        ]
    texto += [
        "",
        "<i>Lo que suele hacer cada mes del primer día al último (la mediana, "
        "para que un año loco no lo tape todo), en dólares. Datos de Binance. Lo "
        "que pasó no tiene por qué repetirse</i>",
    ]
    if e.años < POCOS_AÑOS:
        texto.append(f"<i>Con menos de {POCOS_AÑOS} años es casi azar</i>")
    return "\n".join(texto)


def formatear_diames(
    coin_id: str,
    d: DiasMes,
    incompleto: bool = False,
    hoy: date | None = None,
) -> str:
    """Respuesta de /diames. incompleto si no hay precios de todo el tramo."""
    nombre = escape(coin_id.replace("-", " ").title())
    meses = "1 mes" if d.meses == 1 else f"{d.meses} meses"
    barato, caro = d.barato, d.caro
    texto = [
        f"📆 <b>{nombre}</b> por días del mes, con {meses}",
        "",
        f"🟢 Más barata, el día <b>{barato.dia}</b> ({_pct2(barato.media)})",
        f"🔴 Más cara, el día <b>{caro.dia}</b> ({_pct2(caro.media)})",
        "",
    ]
    tercios = d.tercios()
    mejor = min(tercios, key=lambda t: t[1])[0]
    for tramo, media in tercios:
        marca = " ← el mejor para comprar" if tramo == mejor else ""
        texto.append(f"{tramo}: <b>{_pct2(media)}</b>{marca}")

    dia = (hoy or date.today()).day
    de_hoy = d.de(dia)
    if de_hoy:
        if de_hoy == barato:
            texto.append(f"\nHoy es día {dia}: suele ser su día más barato")
        elif de_hoy == caro:
            texto.append(f"\nHoy es día {dia}: suele ser su día más caro")
        else:
            texto.append(f"\nHoy es día {dia}: suele estar {_pct2(de_hoy.media)}")

    texto.append(
        "<i>Cada día contra la media de las dos semanas de antes y de después. "
        "Sirve para elegir el día de una compra mensual, no para adivinar</i>"
    )
    if d.meses < POCOS_MESES_DIAMES:
        texto.append(
            f"<i>Con menos de {POCOS_MESES_DIAMES} meses es casi azar. Con "
            "HISTORY_DAYS=366 y /rellenar tienes el año entero</i>"
        )
    if incompleto:
        texto.append(f"<i>Solo tengo precios desde el {d.desde:%d/%m/%Y}.</i>")
    return "\n".join(texto)


def formatear_soporte(coin_id: str, s: Soportes, horas: float, currency: str) -> str:
    """Respuesta de /soporte."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    texto = [
        f"🧱 <b>{nombre}</b>: soportes y resistencias, {nombre_periodo(horas)}",
        f"Está a <b>{simbolo}{_num(s.precio)}</b>",
    ]
    if not s.soportes and not s.resistencias:
        texto.append(
            "\nNo ha girado dos veces en el mismo sitio. Prueba con un tramo más "
            f"largo: /soporte {escape(coin_id)} 180d"
        )
        return "\n".join(texto)

    def linea(emoji: str, n: Nivel) -> str:
        toques = f"{n.toques} toques, el último el {n.ultimo:%d/%m}"
        distancia = f"{s.distancia(n):+.1f}%".replace(".", ",")
        return f"{emoji} {simbolo}{_num(n.precio)} · {toques} · <b>{distancia}</b>"

    texto += ["", "<b>Resistencias</b>, por arriba"]
    if s.resistencias:
        texto += [linea("🔴", n) for n in s.resistencias]
    else:
        texto.append("Ninguna por arriba: está por encima de donde ha girado")
    texto += ["", "<b>Soportes</b>, por abajo"]
    if s.soportes:
        texto += [linea("🟢", n) for n in s.soportes]
    else:
        texto.append("Ninguno por abajo: está por debajo de donde ha girado")

    cerca = (s.soportes or s.resistencias)[0]
    texto.append(
        "\n<i>Precios donde ha girado al menos dos veces. Para poner una alerta "
        f"con sentido: /alerta {escape(coin_id)} {_redondo_alerta(cerca.precio)}</i>"
    )
    return "\n".join(texto)


def _redondo_alerta(precio: float) -> str:
    # Tres cifras: 62.345,70 se escribe 62300, que es como lo pondría uno.
    redondo = round(precio, 2 - math.floor(math.log10(precio)))
    return f"{redondo:f}".rstrip("0").rstrip(".")


def formatear_macd(coin_id: str, m: Macd, currency: str) -> str:
    """Respuesta de /macd."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())

    def dinero(valor: float) -> str:
        signo = "-" if valor < 0 else ""
        return f"{signo}{simbolo}{_num(abs(valor))}"

    texto = [f"📶 <b>{nombre}</b>: MACD de {RAPIDA} y {LENTA} días", ""]
    if m.arriba:
        texto.append("🐂 <b>Empuje al alza</b>: el MACD va por encima de su señal")
    else:
        texto.append("🐻 <b>Empuje a la baja</b>: el MACD va por debajo de su señal")

    if m.cruce_hace == 0:
        texto.append("✂️ La ha cruzado hoy")
    elif m.cruce_hace == 1:
        texto.append("✂️ La cruzó ayer")
    elif m.cruce_hace is not None:
        texto.append(f"Desde hace {m.cruce_hace} días")
    else:
        texto.append(f"Así en todos los {m.dias} días que tengo")

    if m.cogiendo_fuerza:
        texto.append("💪 Y cogiendo fuerza")
    else:
        texto.append("🫠 Pero perdiendo fuerza: si sigue así, puede girar pronto")

    fondo = "sube" if m.macd > 0 else "baja"
    texto += [
        f"De fondo {fondo}: la media de {RAPIDA} días va "
        f"{'por encima' if m.macd > 0 else 'por debajo'} de la de {LENTA}",
        "",
        f"MACD {dinero(m.macd)} · Señal {dinero(m.señal)} · "
        f"Diferencia {'+' if m.histograma > 0 else ''}{dinero(m.histograma)}",
        f"<i>La media de {RAPIDA} días menos la de {LENTA}, contra su propia media "
        f"de {SEÑAL_MACD}. Cruzarla hacia arriba suele leerse como compra y hacia "
        "abajo como venta, pero llega con retraso. Sale de lo guardado</i>",
    ]
    return "\n".join(texto)


def formatear_estocastico(coin_id: str, e: Estocastico, currency: str) -> str:
    """Respuesta de /estocastico."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    dias = PERIODO_ESTOCASTICO
    texto = [f"🎚️ <b>{_nombre(coin_id)}</b>: estocástico de {dias} días", ""]
    k = f"{e.k:.0f}"
    if e.zona == "alto":
        texto.append(
            f"🔥 <b>Sobrecompra</b> ({k}): está cerca de lo más alto de las dos "
            "últimas semanas"
        )
    elif e.zona == "bajo":
        texto.append(
            f"🧊 <b>Sobreventa</b> ({k}): está cerca de lo más bajo de las dos "
            "últimas semanas"
        )
    else:
        texto.append(f"⚖️ <b>En medio</b> ({k}): ni cerca del techo ni del suelo")

    hacia = "arriba" if e.cruce_arriba else "abajo"
    if e.cruce_hace == 0:
        texto.append(f"✂️ Hoy ha cruzado su media hacia {hacia}")
    elif e.cruce_hace == 1:
        texto.append(f"✂️ Ayer cruzó su media hacia {hacia}")
    elif e.cruce_hace is not None:
        lado = "encima" if e.cruce_arriba else "debajo"
        texto.append(f"Va por {lado} de su media desde hace {e.cruce_hace} días")

    texto += [
        "",
        f"En {dias} días, entre {simbolo}{_num(e.suelo)} y {simbolo}{_num(e.techo)}"
        f" · ahora {simbolo}{_num(e.ahora)}",
        f"%K {e.k:.0f} · %D {e.d:.0f}",
        f"<i>Dónde está el precio dentro de lo que se ha movido en {dias} días: 100 "
        f"es lo más alto y 0 lo más bajo. Por encima de {ALTO_ESTOCASTICO} suele "
        f"leerse como sobrecompra y por debajo de {BAJO_ESTOCASTICO} como "
        "sobreventa. Se parece al /rsi, pero mira el rango y no la fuerza de las "
        "subidas. Sale de lo guardado</i>",
    ]
    return "\n".join(texto)


def formatear_bollinger(coin_id: str, b: Bandas, currency: str) -> str:
    """Respuesta de /bollinger."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(coin_id.replace("-", " ").title())
    ancho = f"{b.ancho:.1f}".replace(".", ",")
    texto = [
        f"📏 <b>{nombre}</b>: bandas de Bollinger de {PERIODO_BOLLINGER} días",
        "",
        f"Banda alta: {simbolo}{_num(b.alta)}",
        f"Media: {simbolo}{_num(b.media)}",
        f"Banda baja: {simbolo}{_num(b.baja)}",
        "",
    ]
    ahora = f"Está a <b>{simbolo}{_num(b.ahora)}</b>"
    if b.zona == "encima":
        texto.append(
            f"🔥 {ahora}, por encima de la banda alta: muy estirada. Suele "
            "volver hacia la media, aunque en una subida fuerte puede seguir ahí"
        )
    elif b.zona == "debajo":
        texto.append(
            f"🧊 {ahora}, por debajo de la banda baja: muy aplastada. Suele "
            "rebotar hacia la media, aunque en una caída fuerte puede seguir ahí"
        )
    else:
        punto = min(max(b.posicion, 0), 100)
        texto.append(f"{ahora}, dentro de la banda")
        texto.append(f"baja {barra(punto)} alta")

    texto.append(f"\nDe una banda a otra hay un {ancho}%")
    if b.estrecha:
        texto.append(
            "🤏 La banda está de las más estrechas de lo que tengo guardado: "
            "cuando se aprieta así, suele venir un movimiento fuerte, sin saber "
            "hacia dónde"
        )
    texto.append(
        f"<i>La media de {PERIODO_BOLLINGER} días y dos veces lo que se suele "
        "separar de ella, por arriba y por abajo. Sale de lo guardado</i>"
    )
    return "\n".join(texto)


def formatear_sharpe(s: Sharpe, btc: Sharpe | None, dias: int) -> str:
    """Respuesta de /sharpe. btc a None si no hay con qué comparar."""
    ratio = f"{s.ratio:.2f}".replace(".", ",")
    texto = [
        f"📐 <b>Tu Sharpe de los últimos {dias} días: {ratio}</b>",
        f"Nota: {s.nota}",
        "",
        # Lo de verdad y no al año: un mes malo pasado a un año daba -300%.
        f"{_flecha(s.gana)} En estos días: {_decimal(s.gana)}%",
        f"🎢 Se mueve al año: {_decimal(s.se_mueve)}%",
    ]
    if btc:
        suyo = f"{btc.ratio:.2f}".replace(".", ",")
        # Por debajo de 0,1 de diferencia es ruido de unos pocos días.
        if abs(s.ratio - btc.ratio) < 0.1:
            que = "Casi igual que bitcoin"
        elif s.ratio > btc.ratio:
            que = "Mejor que bitcoin"
        else:
            que = "Peor que bitcoin: te saldría más a cuenta tener solo bitcoin"
        texto += ["", f"₿ Bitcoin: {suyo} ({btc.nota})", f"{que}"]

    texto += [
        "",
        f"<i>Lo que gana por cada punto que se mueve, en {s.contados} días con lo "
        "que tienes hoy. De 1 para arriba está bien; no resta lo que daría un "
        "depósito</i>",
    ]
    return "\n".join(texto)


_LUCES = {
    VERDE: ("🟢", "luz verde", "Más señales a favor de comprar que en contra"),
    AMBAR: ("🟡", "luz ámbar", "Señales mezcladas, nada claro"),
}
_ROJA = ("🔴", "luz roja", "Más señales en contra de comprar que a favor")


def formatear_semaforo(
    coin_id: str, votos: list[Voto], luz: str, faltan: list[str]
) -> str:
    """Respuesta de /semaforo. faltan son los indicadores que no se pudieron mirar."""
    nombre = escape(coin_id.replace("-", " ").title())
    emoji, color, resumen = _LUCES.get(luz, _ROJA)
    favor = sum(v.valor > 0 for v in votos)
    contra = sum(v.valor < 0 for v in votos)
    texto = [
        f"{emoji} <b>{nombre}</b>: {color}",
        resumen,
        f"<i>{favor} a favor · {contra} en contra · "
        f"{len(votos) - favor - contra} en medio</i>",
        "",
    ]
    for v in votos:
        marca = "✅" if v.valor > 0 else "❌" if v.valor < 0 else "⚪"
        texto.append(f"{marca} <b>{escape(v.nombre)}</b>: {escape(v.motivo)}")
    texto.append("")
    if faltan:
        texto.append(f"<i>Sin datos de {escape(', '.join(faltan))}</i>")
    texto.append(
        "<i>Junta lo que dicen los indicadores, no es un consejo. El detalle de "
        "cada uno: /rsi, /macd, /bollinger, /media, /miedo y /funding</i>"
    )
    return "\n".join(texto)


def _pct_funding(valor: float) -> str:
    return f"{valor:+.4f}%".replace(".", ",")


def formatear_aviso_funding(f: Funding) -> str:
    """El aviso de /funding btc avisa, al entrar en una de las dos puntas."""
    simbolo = escape(f.par.removesuffix("USDT"))
    tasa = f.ahora if f.semana is None else f.semana
    de_que = "Media de la semana" if f.semana is not None else "Último pago"
    texto = [
        f"{f.emoji} <b>Funding de {simbolo}: {f.nivel.lower()}</b>",
        f"{de_que}: <b>{_pct_funding(tasa)}</b> cada 8 h (lo normal es +0,01%)",
    ]
    if f.que_pasa:
        texto.append(f.que_pasa)
    texto.append(
        f"<i>El detalle, en /funding {simbolo.lower()}. No repito hasta que se "
        "calme y vuelva a pasar</i>"
    )
    return "\n".join(texto)


def formatear_oi(i: Interes, coin_id: str) -> str:
    """Respuesta de /oi."""
    simbolo = escape(i.par.removesuffix("USDT"))
    contratos = [d.contratos for d in i.dias]
    lineas = [
        f"📊 <b>Futuros de {_nombre(coin_id)}</b> · {escape(i.par)} en Binance",
        f"Apostado ahora: <b>{_num(i.hoy.contratos)} {simbolo}</b> "
        f"(unos {grande(i.hoy.valor)} de dólares)",
    ]
    if len(contratos) >= MINIMO_BARRAS:
        lineas.append(f"<code>{sparkline(muestrear(contratos, BARRAS_MOVIL))}</code>")
    tramos = [
        f"{nombre}: {_signo(c)}"
        for dias, nombre in ((1, "24 h"), (7, "7 días"), (30, "30 días"))
        if (c := i.cambio(dias)) is not None
    ]
    lineas.append(" · ".join(tramos))
    if i.maximo and len(contratos) > 7:
        lineas.append("🔝 Lo más alto del último mes")

    emoji, que_pasa = lectura(i)
    dias = min(7, len(i.dias) - 1)
    semana = "la semana" if dias == 7 else f"{_veces(dias, 'día', 'días')}"
    lineas += [
        "",
        f"{emoji} <b>{que_pasa}</b>",
        f"En {semana}, lo apostado {_signo(i.cambio(dias))} y el precio "
        f"{_signo(i.cambio_precio(dias))}.",
        "",
        "<i>Cuento contratos y no dólares, para que una subida del precio no "
        "parezca dinero nuevo. Hacia qué lado apuestan: "
        f"/funding {simbolo.lower()}</i>",
    ]
    return "\n".join(lineas)


def _millones(valor: float, corto: bool) -> str:
    """'12,3 M', '850 mil', con '+' delante si el libro no llegaba."""
    if valor >= 1e6:
        texto = f"{valor / 1e6:.1f} M".replace(".", ",")
    else:
        texto = f"{valor / 1e3:.0f} mil"
    return f"+{texto}" if corto else texto


def formatear_premium(p: Premium) -> str:
    """Respuesta de /premium."""

    def pct(valor: float) -> str:
        # Una media de -0,001 saldría "-0,00%".
        return "0,00%" if abs(valor) < 0.005 else _pct2(valor)

    primas = [h.prima for h in p.horas]
    dias = round(len(p.horas) / 24)
    lineas = [
        f"🇺🇸 <b>Prima de Coinbase: {pct(p.ahora)}</b> · {escape(p.simbolo)}",
        f"Coinbase: ${_num(p.coinbase)} · Binance: ${_num(p.binance)}",
    ]
    if len(primas) >= MINIMO_BARRAS:
        lineas.append(f"<code>{sparkline(muestrear(primas, BARRAS_MOVIL))}</code>")
    if dias >= 1:
        lineas.append(
            f"En {_veces(dias, 'día', 'días')}: media {pct(p.media)}, "
            f"entre {pct(min(primas))} y {pct(max(primas))}"
        )

    if p.lado == "compran":
        lectura = (
            "🟢 <b>Se paga más en Coinbase</b>: compran con ganas en EE. UU., "
            "que es donde compran los fondos"
        )
    elif p.lado == "venden":
        lectura = "🔴 <b>Se paga menos en Coinbase</b>: venden más en EE. UU."
    else:
        lectura = "😐 <b>Casi igual en los dos</b>: nada que destacar"
    lineas += [
        "",
        lectura,
        "",
        "<i>Coinbase es donde compran los grandes de EE. UU. y Binance, el resto. "
        "Al de Binance le quito lo que el USDT se separa del dólar, que si no "
        "parecería prima y no lo es.</i>",
    ]
    return "\n".join(lineas)


def formatear_profundidad(p: Profundidad, coin_id: str) -> str:
    """Respuesta de /profundidad."""
    simbolo = escape(p.par.removesuffix("USDT"))
    filas = [f"{'':5} {'subir':>9} {'bajar':>9}"]
    for t in p.tramos:
        pct = f"{t.pct:g}%".replace(".", ",")
        subir = _millones(t.subir, t.subir_corto)
        bajar = _millones(t.bajar, t.bajar_corto)
        filas.append(f"{pct:5} {subir:>9} {bajar:>9}")

    lineas = [
        f"🧱 <b>Profundidad de {_nombre(coin_id)}</b> · {escape(p.par)} en Binance",
        f"Precio: ${_num(p.precio)}",
        "",
        "Dólares que habría que comprar o vender de golpe para moverlo:",
        "<code>" + "\n".join(filas) + "</code>",
    ]
    if any(t.subir_corto or t.bajar_corto for t in p.tramos):
        lineas.append("<i>Con + es que el libro se acaba antes: hace falta más.</i>")

    if p.lado == "compran":
        lectura = "🛡 <b>Hay más esperando para comprar</b>: hacia abajo aguanta más"
    elif p.lado == "venden":
        lectura = "🧱 <b>Hay más esperando para vender</b>: hacia arriba le cuesta más"
    else:
        lectura = "⚖️ <b>Parecido a los dos lados</b>"
    lineas += [
        "",
        lectura,
        "",
        "<i>Solo cuenta Binance al contado, y las órdenes se ponen y se quitan en "
        "segundos: es una foto de ahora. Cuánto hay apostado en futuros: "
        f"/oi {simbolo.lower()}</i>",
    ]
    return "\n".join(lineas)


def formatear_longshort(ls: LongShort, coin_id: str) -> str:
    """Respuesta de /longshort."""
    simbolo = escape(ls.par.removesuffix("USDT"))

    def pct(valor: float) -> str:
        return f"{valor:.0f}%"

    lineas = [
        f"⚖️ <b>Largos y cortos de {_nombre(coin_id)}</b> · {escape(ls.par)} en Binance",
        f"🔺 {pct(ls.hoy.largos)} apuesta a que sube · "
        f"🔻 {pct(ls.hoy.cortos)} a que baja",
        # Redondeada antes: la barra corta hacia abajo y saldría 70% junto a un 71%.
        _barra_progreso(round(ls.hoy.largos)),
    ]
    largos = [r.largos for r in ls.todos]
    if len(largos) >= MINIMO_BARRAS:
        lineas.append(f"<code>{sparkline(muestrear(largos, BARRAS_MOVIL))}</code>")
    if len(largos) >= 7:
        lineas.append(
            f"Media de {_veces(len(largos), 'día', 'días')}: {pct(ls.media)} a que sube"
        )
    if ls.grandes is not None:
        lineas.append(
            f"Los que más mueven: {pct(ls.grandes.largos)} a que sube, "
            "contando por dinero"
        )

    emoji, que_pasa = lectura_longshort(ls)
    lineas += [
        "",
        f"{emoji} <b>{que_pasa}</b>",
        "",
        "<i>Cuento cuentas, no dinero: uno con 10 € vale lo mismo que una ballena. "
        "Cuando casi todos van al mismo lado, el precio suele ir a pillarlos. "
        f"Cuánto hay apostado: /oi {simbolo.lower()}</i>",
    ]
    return "\n".join(lineas)


def formatear_mayer(m: Mayer, coin_id: str) -> str:
    """Respuesta de /mayer."""

    def multiple(valor: float) -> str:
        return f"{valor:.2f}".replace(".", ",")

    def mes(d) -> str:
        return f"{NOMBRES_MESES[d.cuando.month - 1][:3]} {d.cuando.year}"

    def dolares(valor: float) -> str:
        # En bitcoin los céntimos sobran; en una de céntimos, no.
        return (
            f"${valor:,.0f}".replace(",", ".") if valor >= 1000 else f"${_num(valor)}"
        )

    hoy = m.hoy
    emoji, zona = m.zona
    lineas = [
        f"📐 <b>Múltiplo de Mayer de {_nombre(coin_id)}: {multiple(hoy.multiple)}</b>",
        f"Precio: {dolares(hoy.precio)} · media de 200 días: {dolares(m.media)}",
    ]
    ultimo_año = [d.multiple for d in m.dias[-365:]]
    if len(ultimo_año) >= MINIMO_BARRAS:
        lineas.append(f"<code>{sparkline(muestrear(ultimo_año, BARRAS_MOVIL))}</code>")
    lineas += [
        "",
        f"{emoji} <b>{zona}</b>",
        f"Desde {m.dias[0].cuando.year}, el {m.por_debajo:.0f}% de los días "
        "estuvo más bajo que hoy.",
        f"Lo más alto: {multiple(m.maximo.multiple)} en {mes(m.maximo)} · "
        f"lo más bajo: {multiple(m.minimo.multiple)} en {mes(m.minimo)}",
    ]
    if hoy.multiple < 1:
        lineas.append(
            f"Para volver a su media tendría que subir a {dolares(m.media)} "
            f"({_signo((m.media / hoy.precio - 1) * 100)})."
        )
    if hoy.multiple < BURBUJA:
        lineas.append(
            f"Zona de burbuja (2,4): a partir de {dolares(m.media * BURBUJA)}."
        )
    lineas += [
        "",
        "<i>El precio entre su media de 200 días, en dólares. Por debajo de 1 "
        "está más barato que de media en los últimos siete meses; por encima de "
        "2,4 solía ser burbuja. Se pensó para bitcoin: en otras dice menos.</i>",
    ]
    return "\n".join(lineas)


def formatear_funding(f: Funding, avisa: bool = False) -> str:
    """Respuesta de /funding. avisa, si tienes puesto el aviso de esa."""
    simbolo = escape(f.par.removesuffix("USDT"))

    def pct(valor: float) -> str:
        return f"{valor:+.4f}%".replace(".", ",")

    texto = [
        f"{f.emoji} <b>Funding de {simbolo}: {pct(f.ahora)}</b> cada 8 h",
        f"<b>{f.nivel}</b>",
    ]
    if f.que_pasa:
        texto.append(f.que_pasa)
    texto.append("")
    if f.semana is not None:
        texto.append(f"Media de la semana: {pct(f.semana)}")
    texto.append(f"Al año serían un {_decimal(f.al_año)}%")
    if avisa:
        texto += [
            "",
            f"🔔 Te aviso si se va a un extremo. Para quitarlo: /funding "
            f"{simbolo.lower()} no",
        ]
    texto += [
        "",
        "<i>Lo que pagan cada 8 h los que apuestan a que sube a los que apuestan "
        "a que baja; en negativo, al revés. Lo normal es +0,01%. Datos de los "
        "futuros de Binance</i>",
    ]
    return "\n".join(texto)


def formatear_futuro(f: Futuro, currency: str) -> str:
    """Respuesta de /futuro."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    cuando = "mañana" if f.dias == 1 else f"dentro de {f.dias} días"

    def entre(rango: tuple[float, float]) -> str:
        return f"entre {simbolo}{_num(rango[0])} y {simbolo}{_num(rango[1])}"

    al_dia = f"{f.al_dia:.1f}".replace(".", ",")
    return "\n".join(
        [
            f"🔮 <b>Tu cartera {cuando}</b>",
            f"Hoy vale <b>{simbolo}{_num(f.valor)}</b>",
            "",
            f"🎯 2 de cada 3 veces: {entre(f.probable)}",
            f"🛟 9 de cada 10: {entre(f.casi_seguro)}",
            "",
            f"<i>Según lo que se ha movido en los últimos {f.contados} días, un "
            f"{al_dia}% al día, con lo que tienes hoy. No es una predicción: no "
            "dice si sube o baja, solo cuánto suele moverse. Un desplome de los "
            "gordos se sale de aquí</i>",
        ]
    )


def formatear_dominancia(d: Dominancia) -> str:
    """Respuesta de /dominancia."""
    m = d.ahora

    def pct(valor: float) -> str:
        return f"{valor:.1f}%".replace(".", ",")

    texto = [f"👑 <b>Dominancia de Bitcoin: {pct(m.bitcoin)}</b>", ""]
    for dias, puntos in d.cambios:
        tramo = "24 h" if dias == 1 else f"{dias} días"
        cambio = f"{puntos:+.1f}".replace(".", ",")
        texto.append(f"{_flecha(puntos)} {cambio} puntos en {tramo}")
    if not d.cambios:
        texto.append(
            "Aún no tengo de días anteriores para comparar: guardo una al día "
            "mientras está en marcha con --loop"
        )

    if d.hacia == "bitcoin":
        texto.append("\n🟠 El dinero vuelve a bitcoin: las altcoins pierden peso")
    elif d.hacia == "altcoins":
        texto.append("\n🌈 El dinero se va a las altcoins: bitcoin pierde peso")
    elif d.hacia == "":
        texto.append("\n⚖️ Ni a un lado ni a otro: se reparte más o menos igual")

    texto.append("")
    if m.ethereum is not None:
        texto.append(f"Ethereum: {pct(m.ethereum)}")
    if m.estables is not None:
        texto.append(f"Estables: {pct(m.estables)}")
    if m.resto is not None:
        texto.append(f"El resto de altcoins: {pct(m.resto)}")
    texto.append(
        "<i>Qué parte de todo el mercado es bitcoin. Si sube aunque bitcoin "
        "baje, las demás bajan más</i>"
    )
    return "\n".join(texto)


def _pct2(valor: float) -> str:
    return f"{valor:+.2f}%".replace(".", ",")


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


def formatear_vuelta(e: Equilibrio, currency: str) -> str:
    """Aviso de que una que perdía ya vale lo que te costó."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(e.coin_id.replace("-", " ").title())
    return (
        f"🟢 <b>{nombre}</b> vuelve a lo que te costó, {simbolo}{_num(e.medio)}\n"
        f"Ahora está a <b>{simbolo}{_num(e.precio)}</b>. Ya no pierdes con ella."
    )


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
