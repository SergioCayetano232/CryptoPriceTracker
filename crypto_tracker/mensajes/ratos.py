"""Juegos, frases y curiosidades para pasar el rato."""

from datetime import date

from ..adios import Adios
from ..adivina import Intento
from ..ballena import Ballena
from ..caraocruz import QUE_HACER
from ..cumple import Cumple
from ..dado import CARAS
from ..dado import QUE_HACER as QUE_HACER_DADO
from ..equivalencias.enletras import dinero as dinero_en_letras
from ..equivalencias.mundo import PERSONAS, Mundo
from ..equivalencias.pizza import BTC, Pizza
from ..ethereum import Ethereum
from ..frase import Frase
from ..galleta import Galleta
from ..glosario import TERMINOS, buscar, parecido
from ..horoscopo import Horoscopo
from ..indicadores.dia import Dia
from ..indicadores.diasemana import NOMBRES
from ..indicadores.halving import Halving
from ..indicadores.mercado import grande
from ..indicadores.millonario import Millonario, cantidad
from ..indicadores.rango import barra
from ..indicadores.redondo import Redondo
from ..indicadores.sat import CANTIDADES as CANTIDADES_SAT
from ..indicadores.sat import SATS_POR_BTC, Sat
from ..merge import Merge
from ..nucleo.telegram import escape
from ..ppt import EMOJIS as EMOJIS_PPT
from ..ppt import QUE_HACER as QUE_HACER_PPT
from ..quiz import PREGUNTAS as PREGUNTAS_QUIZ
from ..tarot import Carta
from ..version import Version
from ..whitepaper import Whitepaper
from .base import SIMBOLOS, _es, _flecha, _num


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


def formatear_apodo(apodo: tuple[str, str, str]) -> str:
    """Respuesta de /apodo."""
    emoji, mote, porque = apodo
    return f"{emoji} Te llamaremos <b>{mote}</b>\n<i>{porque}</i>"


def formatear_enletras(valor: float, currency: str) -> str:
    """Respuesta de /enletras."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    return (
        "✍️ <b>Tu cartera, en letras</b>\n"
        f"{dinero_en_letras(valor, currency)}\n"
        f"<i>{simbolo}{_num(valor)}</i>"
    )


def formatear_quiz(numero: int) -> tuple[str, list[list[tuple[str, str]]]]:
    """La pregunta de /quiz y un botón por respuesta, cada uno en su fila."""
    p = PREGUNTAS_QUIZ[numero]
    botones = [[(o, f"/quiz {numero} {i}")] for i, o in enumerate(p.opciones)]
    return f"❓ <b>{escape(p.texto)}</b>", botones


def formatear_respuesta_quiz(
    numero: int, respuesta: int
) -> tuple[str, list[list[tuple[str, str]]]]:
    """Lo que sale al pulsar una respuesta, con el botón para otra."""
    p = PREGUNTAS_QUIZ[numero]
    buena = escape(p.opciones[p.buena])
    if respuesta == p.buena:
        texto = f"✅ <b>¡Bien!</b> Era {buena}"
    else:
        dicha = escape(p.opciones[respuesta])
        texto = f"❌ <b>Casi</b>\nDijiste «{dicha}», era <b>{buena}</b>"
    return f"{texto}\n<i>{escape(p.texto)}</i>", [[("🎲 Otra pregunta", "/quiz")]]


def formatear_dato(dato: str) -> str:
    """Respuesta de /dato."""
    return f"🤓 <b>¿Sabías que…?</b>\n{escape(dato)}"


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
