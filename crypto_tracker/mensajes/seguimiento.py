"""Alertas puestas, stops, recordatorios y lo que vigilas."""

from datetime import date, datetime, time

from ..cada import EJEMPLO as EJEMPLO_CADA
from ..cada import Programado
from ..calma import VENTANA as VENTANA_CALMA
from ..calma import Calma
from ..condicion import Condicion
from ..config import Watch
from ..emocion import EMOCIONES, Emociones, en_frase
from ..emocion import Grupo as GrupoEmocion
from ..escalera import Escalera
from ..fantasma import BITCOIN as BITCOIN_FANTASMA
from ..fantasma import EMPATE as EMPATE_FANTASMA
from ..fantasma import Fantasma
from ..herencia import Linea
from ..maximo import hace
from ..miedo import Indice
from ..miedo import nombre as nombre_miedo
from ..movimientos import texto_cantidad
from ..pienso import IGUAL as IGUAL_PIENSO
from ..pienso import SUBIDON, Pienso
from ..prediccion import Marcador, Prediccion
from ..puntuales import CARTERA, Puntual, ejemplo, progreso
from ..recordar import Recordatorio
from ..rezagada import EJEMPLO as EJEMPLO_REZAGADA
from ..rezagada import Rezagada
from ..stop import Stop
from ..telegram import escape
from .base import (
    SIMBOLOS,
    _barra_progreso,
    _falta,
    _flecha,
    _ganancia,
    _nombre,
    _num,
    _pct,
    _quien_condicion,
    _signo,
    describir,
)


def _hora(hora: time) -> str:
    return f"{hora.hour}:{hora.minute:02d}"


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


def formatear_pienso(
    p: Pienso,
    currency: str,
    cambio_24h: float | None,
    indice: Indice | None,
    rsi: float | None,
) -> str:
    """Respuesta a /pienso: lo que hay ahora, para pensarlo con calma."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        "🧊 <b>Vale, lo pensamos 24 h</b>",
        f"Quieres meter {simbolo}{_num(p.importe)} en <b>{_nombre(p.coin_id)}</b>, "
        f"que está a {simbolo}{_num(p.precio)}.",
        "",
    ]
    if cambio_24h is not None:
        linea = f"{_flecha(cambio_24h)} {cambio_24h:+.2f}% en 24 h"
        if cambio_24h >= SUBIDON:
            linea += ": comprar justo después de un subidón suele salir caro"
        texto.append(linea)
    if indice is not None:
        emoji, nombre = nombre_miedo(indice)
        texto.append(f"{emoji} Miedo y codicia: {indice.valor} ({nombre.lower()})")
    if rsi is not None:
        zona = ": sobrecompra" if rsi >= 70 else ": sobreventa" if rsi <= 30 else ""
        texto.append(f"📊 RSI {rsi:.0f}{zona}")
    if texto[-1]:
        texto.append("")

    texto.append(
        f"Mañana a las {p.pregunta.astimezone():%H:%M} te pregunto otra vez con el "
        f"precio de entonces. Si lo descartas antes: /pienso {escape(p.coin_id)} no"
    )
    return "\n".join(texto)


def documento_herencia(
    lista: list[Linea], nota: str | None, hoy: date, currency: str
) -> str:
    """El papel para tu familia, en texto sin formato para guardarlo o imprimirlo."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        f"LO QUE TENGO EN CRIPTOMONEDAS · a {hoy:%d/%m/%Y}",
        "",
        "Este papel NO lleva ninguna clave ni contraseña. Dice qué hay y dónde.",
        "",
    ]
    for li in lista:
        valor = (
            f" (unos {simbolo}{_num(li.valor)} a {hoy:%d/%m/%Y})" if li.valor else ""
        )
        texto += [
            f"- {li.coin_id.replace('-', ' ').title()}: "
            f"{texto_cantidad(li.cantidad)}{valor}",
            f"  Dónde: {li.donde or 'sin apuntar'}",
        ]
    total = sum(li.valor for li in lista if li.valor)
    if total:
        texto += ["", f"En total, unos {simbolo}{_num(total)} a {hoy:%d/%m/%Y}."]
    if nota:
        texto += ["", f"Nota: {nota}"]
    texto += ["", "QUÉ HACER", *PASOS_HERENCIA]
    return "\n".join(texto)


PASOS_HERENCIA = [
    "1. No se lo des a nadie que te escriba ofreciendo ayuda para recuperarlo: es "
    "la estafa más común. Ninguna empresa seria te pedirá la frase de recuperación.",
    "2. Lo que esté en un exchange (Binance, Coinbase, Kraken...): escribe a su "
    "soporte con el certificado de defunción. Los grandes suelen tener un proceso "
    "para herederos.",
    "3. Lo que esté en una cartera propia (Ledger, Trezor, una app del móvil): "
    "hace falta su frase de recuperación, que no está aquí. Búscala donde dice "
    "cada línea.",
    "4. El valor de arriba es orientativo: los precios cambian cada día.",
    "5. Entra en el impuesto de sucesiones como cualquier otro bien: díselo a "
    "quien lleve la herencia.",
]


def pie_herencia(lista: list[Linea], hoy: date) -> str:
    sin = sum(1 for li in lista if not li.donde)
    texto = (
        "📜 <b>Lo que tienes y dónde, para tu familia</b>\n"
        "Guárdalo o imprímelo junto a tus papeles. No lleva ninguna clave."
    )
    if sin:
        cual = "1 cripto" if sin == 1 else f"{sin} criptos"
        texto += (
            f"\n⚠️ {cual} sin decir dónde está. Apúntalo así: "
            "/herencia btc Ledger en el cajón del escritorio"
        )
    return texto + f"\n<i>Vuelve a pedirlo cuando cambie la cartera ({hoy:%d/%m})</i>"


def formatear_aviso_calma(coin_id: str, c: Calma, currency: str) -> str:
    """El aviso de cuando una se queda mucho más quieta de lo normal."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        f"🤫 <b>{_nombre(coin_id)}</b> lleva {VENTANA_CALMA} días muy quieta",
        f"Entre {simbolo}{_num(c.suelo)} y {simbolo}{_num(c.techo)}: se ha movido "
        f"un {c.rango:.1f}%, cuando lo normal en una semana es un {c.normal:.1f}%.",
    ]
    if c.despues is not None:
        texto.append(
            f"Las otras {c.veces} veces que estuvo así, la semana siguiente se movió "
            f"un {c.despues:.1f}% de media, hacia un lado u otro."
        )
    texto.append(
        "<i>Se dice que una calma así va antes de un movimiento fuerte, pero no "
        "hacia dónde, y no siempre se cumple: mira la línea de arriba. Si quieres "
        "enterarte: /alerta</i>"
    )
    return "\n".join(texto)


def formatear_calma(lista: list[tuple[str, Calma | None]]) -> str:
    """/tormenta: cuánto se mueven esta semana las que vigilas, contra lo normal."""
    texto = [f"🤫 <b>Lo quietas que están</b> · últimos {VENTANA_CALMA} días", ""]
    for coin_id, c in lista:
        if c is None:
            texto.append(f"<b>{_nombre(coin_id)}</b>: aún no tengo historia bastante")
            continue
        linea = (
            f"<b>{_nombre(coin_id)}</b>: {c.rango:.1f}% (lo normal, {c.normal:.1f}%)"
        )
        if c.quieta:
            linea += " · 🤫 muy quieta"
        texto.append(linea)
    texto.append(
        "\n<i>Lo que se ha movido entre lo más alto y lo más bajo de la semana. "
        "Muy quieta es de las semanas más tranquilas de lo guardado; se dice que va "
        "antes de un movimiento fuerte. Para que te avise: AVISO_CALMA=si</i>"
    )
    return "\n".join(texto)


def formatear_emociones(e: Emociones) -> str:
    """/emociones: con qué ánimo compras y vendes, y cómo te ha ido con cada uno."""
    texto = ["🎭 <b>Con qué ánimo compras y vendes</b>"]
    if e.compras:
        texto += ["", "<b>Compras</b>", *(_grupo_emocion(g, "hoy") for g in e.compras)]
    if e.ventas:
        texto += [
            "",
            "<b>Ventas</b>",
            *(_grupo_emocion(g, "hoy valdría") for g in e.ventas),
        ]

    par = e.mejor_y_peor()
    if par:
        mejor, peor = par
        texto += [
            "",
            f"👉 Tus mejores compras son con {en_frase(mejor.emocion)} "
            f"({mejor.cambio:+.1f}%) y las peores con {en_frase(peor.emocion)} "
            f"({peor.cambio:+.1f}%)",
        ]
    texto.append(
        "\n<i>En las compras, lo que valen hoy contra lo que pagaste. En las "
        "ventas, lo que valdría hoy lo vendido contra lo que te dieron: si sube, "
        "vendiste antes de tiempo</i>"
    )
    if e.sin:
        cuantos = "1 movimiento" if e.sin == 1 else f"{e.sin} movimientos"
        texto.append(f"<i>{cuantos} sin ánimo apuntado: /emocion 12 miedo</i>")
    return "\n".join(texto)


def _grupo_emocion(g: GrupoEmocion, como: str) -> str:
    icono, nombre = EMOCIONES[g.emocion]
    linea = f"{icono} {nombre}: {g.veces}"
    if g.cambio is not None:
        linea += f" · {como} {_flecha(g.cambio)} {g.cambio:+.1f}%"
    return linea


def formatear_fantasma(f: Fantasma, precios: dict[str, float], currency: str) -> str:
    """/fantasma a secas: cómo va la cartera de mentira."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = [
        f"👻 <b>Tu cartera fantasma</b> · desde el {f.inicio.astimezone():%d/%m/%Y}",
        "",
    ]
    for coin_id, h in sorted(f.posiciones.items()):
        precio = precios.get(coin_id)
        linea = f"<b>{_nombre(coin_id)}</b> {texto_cantidad(h.cantidad)}"
        if precio is not None and h.invertido:
            vale = h.cantidad * precio
            cambio = _redondo((vale / h.invertido - 1) * 100)
            linea += (
                f" · {simbolo}{_num(h.invertido)} → {simbolo}{_num(vale)} "
                f"({_flecha(cambio)} {cambio:+.1f}%)"
            )
        texto.append(linea)
    texto.append(f"💶 Sin invertir: {simbolo}{_num(f.caja)}")

    valor = f.valor(precios)
    if valor is None:
        texto.append("\n<i>Ahora no tengo el precio de todas: sin total</i>")
        return "\n".join(texto)
    cambio = _redondo((valor / f.importe - 1) * 100)
    texto += [
        "",
        f"Total: <b>{simbolo}{_num(valor)}</b> de {simbolo}{_num(f.importe)} "
        f"({_flecha(cambio)} {cambio:+.1f}%)",
    ]
    btc = precios.get(BITCOIN_FANTASMA)
    en_btc = f.en_bitcoin(btc) if btc else None
    if en_btc is not None:
        cambio_btc = _redondo((en_btc / f.importe - 1) * 100)
        texto.append(
            f"Dejándolo todo en bitcoin el primer día: {simbolo}{_num(en_btc)} "
            f"({_flecha(cambio_btc)} {cambio_btc:+.1f}%)"
        )
        if f.operaciones:
            diferencia = (valor / en_btc - 1) * 100
            if abs(diferencia) < EMPATE_FANTASMA:
                texto.append("👉 Vas igual que si no hubieras hecho nada con bitcoin")
            elif diferencia > 0:
                texto.append("👉 Le ganas a no hacer nada con bitcoin")
            else:
                texto.append("👉 No hacer nada con bitcoin te habría ido mejor")
    veces = "1 operación" if f.operaciones == 1 else f"{f.operaciones} operaciones"
    texto.append(
        f"\n<i>Dinero de mentira, sin comisiones · {veces}. "
        "/fantasma compra btc 200 · /fantasma vende btc todo</i>"
    )
    return "\n".join(texto)


def _redondo(cambio: float) -> float:
    """Sin el -0.0% con flecha roja que sale de un céntimo de diferencia."""
    return round(cambio, 1) + 0.0


def formatear_fantasma_nueva(importe: float, currency: str) -> str:
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    return (
        f"👻 Cartera fantasma nueva con {simbolo}{_num(importe)} de mentira. "
        "Prueba: /fantasma compra btc 200"
    )


def formatear_operacion_fantasma(
    compra: bool,
    coin_id: str,
    euros: float,
    precio: float,
    f: Fantasma,
    currency: str,
) -> str:
    """Respuesta a /fantasma compra o vende."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    verbo = "Comprado" if compra else "Vendido"
    return (
        f"👻 {verbo}: {simbolo}{_num(euros)} de <b>{_nombre(coin_id)}</b> a "
        f"{simbolo}{_num(precio)} ({texto_cantidad(euros / precio)})\n"
        f"Te quedan {simbolo}{_num(f.caja)} sin invertir. Cómo va: /fantasma"
    )


def formatear_prediccion(p: Prediccion, currency: str) -> str:
    """Respuesta a /prediccion btc 70000."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    cambio = (p.predicho / p.entonces - 1) * 100
    verbo = "sube" if cambio > 0 else "baja"
    return (
        f"🔮 Apuntado: <b>{_nombre(p.coin_id)}</b> a "
        f"<b>{simbolo}{_num(p.predicho)}</b> el domingo "
        f"{p.cierre.astimezone():%d/%m a las %H:%M}\n"
        f"Ahora está a {simbolo}{_num(p.entonces)}: dices que {verbo} un "
        f"{abs(cambio):.1f}%.\n"
        "Ese día te digo cómo ha quedado y lo sumo a tu marcador. Hasta un día "
        "antes la puedes cambiar con otra /prediccion."
    )


def formatear_predicciones(
    pendientes: list[Prediccion], m: Marcador | None, currency: str
) -> str:
    """/prediccion a secas: lo que tienes en juego y tu marcador."""
    if not pendientes and m is None:
        return (
            "No has hecho ninguna. Di a cuánto estará el domingo: "
            "/prediccion btc 70000, y llevo la cuenta de cuánto aciertas"
        )
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = []
    if pendientes:
        texto.append("🔮 <b>En juego</b>")
        texto += [
            f"<b>{_nombre(p.coin_id)}</b> a {simbolo}{_num(p.predicho)} el "
            f"{p.cierre.astimezone():%d/%m}"
            for p in pendientes
        ]
    if m is not None:
        if texto:
            texto.append("")
        texto += _marcador(m)
    return "\n".join(texto)


def formatear_resultado(hechas: list[Prediccion], m: Marcador, currency: str) -> str:
    """El domingo: cómo han quedado y el marcador."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    texto = ["🔮 <b>Tus predicciones del domingo</b>"]
    for p in hechas:
        lado = "subía" if p.predicho > p.entonces else "bajaba"
        acierto = (
            f"✅ acertaste que {lado}" if p.acierta_lado else f"❌ dijiste que {lado}"
        )
        quieto = "le ganas" if p.gana_al_quieto else "te gana"
        texto += [
            "",
            f"<b>{_nombre(p.coin_id)}</b>: dijiste {simbolo}{_num(p.predicho)} y quedó "
            f"en <b>{simbolo}{_num(p.real)}</b>",
            f"Te fuiste un {p.error:.1f}% · {acierto} (estaba a "
            f"{simbolo}{_num(p.entonces)})",
            f"<i>Decir «se queda igual» se iba un {p.error_quieto:.1f}%: {quieto}</i>",
        ]
    return "\n".join([*texto, "", *_marcador(m)])


def _marcador(m: Marcador) -> list[str]:
    domingos = "1 predicción" if m.total == 1 else f"{m.total} predicciones"
    lineas = [
        f"📊 <b>Tu marcador</b> ({domingos})",
        f"Hacia dónde iba: <b>{m.lado} de {m.total}</b> (una moneda, la mitad)",
        f"Te vas de media un {m.error_medio:.1f}%",
        f"Más cerca que «se queda igual»: {m.al_quieto} de {m.total}",
    ]
    if m.mejor_que_moneda is None:
        lineas.append("<i>Con menos de 4 aún es pronto para saber si tienes ojo</i>")
    elif m.mejor_que_moneda:
        lineas.append("👉 Le ganas a una moneda al aire")
    else:
        lineas.append("👉 Una moneda al aire lo haría igual o mejor")
    return lineas


def formatear_piensos(lista: list[Pienso], currency: str) -> str:
    """/pienso a secas."""
    if not lista:
        return (
            "No te estás pensando ninguna compra. Antes de la próxima: /pienso btc "
            "500, y te pregunto otra vez a las 24 h"
        )
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    lineas = ["🧊 <b>Lo que te estás pensando</b>", ""]
    for p in lista:
        lineas.append(
            f"<b>{_nombre(p.coin_id)}</b> {simbolo}{_num(p.importe)} · te pregunto el "
            f"{p.pregunta.astimezone():%d/%m a las %H:%M}"
        )
    return "\n".join(lineas)


def formatear_pensado(p: Pienso, precio: float, currency: str) -> str:
    """La pregunta de las 24 h."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    cambio = p.cambio(precio)
    texto = (
        f"🧊 <b>¿Sigues queriendo {_nombre(p.coin_id)} por "
        f"{simbolo}{_num(p.importe)}?</b>\n"
        f"Ayer {simbolo}{_num(p.precio)} → ahora <b>{simbolo}{_num(precio)}</b> "
        f"({_flecha(cambio)} {cambio:+.2f}%)\n"
    )
    if cambio <= -IGUAL_PIENSO:
        texto += (
            f"Esperar te ha salido bien: con lo mismo te llevas un "
            f"{(p.precio / precio - 1) * 100:.1f}% más."
        )
    elif cambio >= IGUAL_PIENSO:
        texto += "Ha seguido subiendo. Si aún lo ves claro, adelante."
    else:
        texto += "Está más o menos igual: pensarlo no te ha costado nada."
    return texto + "\nSi la haces, dale al botón y la apunto en la cartera."


def texto_condicion(c: Condicion) -> str:
    """'el miedo por debajo de 20', para /alerta y /alertas."""
    quien = _quien_condicion(c).lower().replace("rsi", "RSI")
    return f"{quien} por {'debajo' if c.menor else 'encima'} de {c.valor:g}"


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
    if alerta.condicion:
        texto += (
            f"\n🔗 Y solo si además está {texto_condicion(alerta.condicion)}. Si "
            "llega al precio antes, espero a que se cumplan las dos"
        )
    if alerta.nota:
        texto += f"\n📝 {escape(alerta.nota)}"
    return texto


def formatear_pareja(
    arriba: Puntual, abajo: Puntual, precio: float, currency: str
) -> str:
    """Respuesta a /alerta bitcoin 60000 o 80000."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    if arriba.coin_id == CARTERA:
        nombre, ahora = "tu cartera", "Ahora vale"
    else:
        nombre = escape(arriba.coin_id.replace("-", " ").title())
        ahora = "Ahora está a"
    texto = (
        f"🎯 Te aviso cuando <b>{nombre}</b> suba a "
        f"<b>{simbolo}{_num(arriba.objetivo)}</b> o baje a "
        f"<b>{simbolo}{_num(abajo.objetivo)}</b>, lo que pase antes.\n"
        f"{ahora} {simbolo}{_num(precio)}. Cuando salte una, quito la otra."
    )
    if arriba.caduca:
        cuando = arriba.caduca.astimezone()
        texto += f"\n⌛ Si no llega ninguna, se borran el {cuando:%d/%m a las %H:%M}."
    if arriba.condicion:
        texto += f"\n🔗 Y solo si además está {texto_condicion(arriba.condicion)}"
    if arriba.nota:
        texto += f"\n📝 {escape(arriba.nota)}"
    return texto


def formatear_pareja_quitada(quitadas: list[Puntual], currency: str) -> str:
    """Debajo del aviso: la otra de la pareja, que ya no hace falta."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    precios = " y ".join(f"{simbolo}{_num(a.objetivo)}" for a in quitadas)
    return f"🔗 Quito la otra de la pareja, la de {precios}."


def formatear_programados(lista: list[Programado]) -> str:
    """Respuesta de /cada a secas."""
    if not lista:
        return f"No tienes nada programado. Por ejemplo: {escape(EJEMPLO_CADA)}"
    lineas = ["⏰ <b>Lo que te mando solo</b>", ""]
    for p in lista:
        lineas.append(f"<code>{p.numero}</code>  {p.cuando}: {escape(p.comando)}")
    lineas.append(f"\nPara quitar uno: /cada quitar {lista[0].numero}")
    return "\n".join(lineas)


def formatear_rezagadas(lista: list[Rezagada]) -> str:
    """Respuesta de /rezagada a secas."""
    if not lista:
        return f"No vigilas ninguna así. Por ejemplo: {EJEMPLO_REZAGADA}"
    lineas = ["🐢 <b>Te aviso si se quedan atrás</b>", ""]
    for r in lista:
        lineas.append(
            f"<b>{_nombre(r.coin_id)}</b> contra {_nombre(r.contra)}: "
            f"{_pct(r.porcentaje)}% peor en 7 días"
        )
    primera = lista[0]
    lineas.append(f"\nPara quitar una: /rezagada {primera.coin_id} {primera.contra} no")
    return "\n".join(lineas)


def formatear_aviso_rezagada(
    r: Rezagada, dif: float, propia: float, contra: float
) -> str:
    """Cuando una lleva la semana haciéndolo mucho peor que la otra."""
    una, otra = _nombre(r.coin_id), _nombre(r.contra)
    return (
        f"🐢 <b>{una}</b> se queda atrás: en 7 días va un "
        f"<b>{dif:+.1f}%</b> frente a {otra}\n"
        f"<i>{una} {propia:+.1f}% · {otra} {contra:+.1f}%</i>"
    )


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
        texto += "\n<i>Si compras o vendes, lo muevo solo a tu nuevo precio medio.</i>"
    return texto


def formatear_stop_movil(
    coin_id: str,
    porcentaje: float,
    ahora: float,
    objetivo: float,
    numero: int,
    currency: str,
) -> str:
    """Respuesta al crear un /stop movil."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    es_cartera = coin_id == CARTERA
    nombre = "tu cartera" if es_cartera else escape(coin_id.replace("-", " ").title())
    esta = "vale" if es_cartera else "está a"
    return (
        f"🛑 Te aviso si <b>{nombre}</b> baja un {_pct(abs(porcentaje))}% desde lo "
        "más alto que toque.\n"
        f"Ahora {esta} {simbolo}{_num(ahora)}, así que hoy saltaría a "
        f"<b>{simbolo}{_num(objetivo)}</b>. Si sube, el aviso sube con ella; si "
        "baja, se queda donde estaba.\n"
        f"Es la número {numero} de /alertas."
    )


def formatear_stop_pasado(s: Stop) -> str:
    """/stop a un % por el que ya has pasado: saltaría en el siguiente ciclo."""
    nombre, coste, _ = _stop_quien(s)
    return (
        f"Con <b>{nombre}</b> ya vas {_signo(s.llevas)} sobre {coste}, "
        f"más allá del {_pct(s.porcentaje)}%. Ponlo más lejos o mira /cartera"
    )


def formatear_escalera(e: Escalera, numeros: list[int], currency: str) -> str:
    """Respuesta al poner una /escalera."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(e.coin_id.replace("-", " ").title())
    cuanto = "todo lo que tienes"
    if e.porcentaje < 100:
        cuanto = f"el {_pct(e.porcentaje)}%"
    lineas = [
        f"🪜 <b>Escalera de venta de {nombre}</b>",
        f"Vendes {cuanto} ({texto_cantidad(e.vendido)}) en "
        f"{len(e.escalones)} escalones:",
        "",
    ]
    for i, x in enumerate(e.escalones, 1):
        linea = (
            f"{i}. A <b>{simbolo}{_num(x.precio)}</b>: vende "
            f"{texto_cantidad(x.cantidad)} → {simbolo}{_num(x.cobrado)}"
        )
        if x.ganancia is not None:
            linea += f"  <i>({_ganancia(x.ganancia, simbolo)}"
            if x.hacienda and x.hacienda > 0:
                linea += f", a Hacienda {simbolo}{_num(x.hacienda)}"
            linea += ")</i>"
        lineas.append(linea)

    lineas += ["", f"Si llega arriba del todo, cobrarías {simbolo}{_num(e.cobrado)}"]
    if e.ganancia is None:
        lineas.append("No sé lo que te costó, así que no saco lo que ganarías.")
    else:
        lineas.append(
            f"{_flecha(e.ganancia)} Le sacarías <b>{_ganancia(e.ganancia, simbolo)}</b>"
        )
        if e.hacienda and e.hacienda > 0:
            lineas.append(f"💸 A Hacienda, unos <b>{simbolo}{_num(e.hacienda)}</b>")
    if e.queda > 0:
        lineas.append(f"Te quedarían {texto_cantidad(e.queda)}")

    cuales = ", ".join(str(n) for n in numeros[:-1]) + f" y {numeros[-1]}"
    lineas += [
        "",
        f"Te aviso al llegar a cada uno: son las alertas {cuales} de /alertas.",
        "<i>No vendo ni apunto nada. Hacienda, con FIFO, sin comisiones y "
        "como si todos los escalones cayeran este año.</i>",
    ]
    if currency.lower() != "eur":
        lineas.append(
            f"<i>Ojo: va en {currency.upper()}, y Hacienda lo quiere en euros.</i>"
        )
    return "\n".join(lineas)


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
    parejas: dict[int, int] | None = None,
) -> str:
    """Respuesta de /alertas. Con precios, dice cuanto le falta a cada una."""
    if not alertas:
        return "No tienes alertas puestas. Crea una con /alerta bitcoin 70000"

    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    lineas = ["🎯 <b>Tus alertas</b>", ""]
    puestas = {a.id for a in alertas}
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
        if a.condicion:
            lineas.append(f"      🔗 si {texto_condicion(a.condicion)}")
        otra = (parejas or {}).get(a.id)
        # Si quitaste la otra a mano, esta ya va sola aunque quede la fila.
        if otra in puestas:
            lineas.append(
                f"      🔗 <i>va con la {otra}: si salta una, quito la otra</i>"
            )
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
