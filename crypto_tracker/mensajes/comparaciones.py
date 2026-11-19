"""Cuánto de cada cosa te compras con lo que tienes."""

from ..aceite import PRECIO as PRECIO_ACEITE
from ..aceite import Aceite
from ..airpods import PRECIO as PRECIO_AIRPODS
from ..airpods import Airpods
from ..alquiler import PRECIO as PRECIO_ALQUILER
from ..alquiler import Alquiler
from ..ave import PRECIO as PRECIO_AVE
from ..ave import Ave
from ..bici import PRECIO as PRECIO_BICI
from ..bici import Bici
from ..bigmac import PRECIO as PRECIO_BIGMAC
from ..bigmac import BigMac
from ..boda import PRECIO as PRECIO_BODA
from ..boda import Boda
from ..cafe import PRECIO as PRECIO_CAFE
from ..cafe import Cafe
from ..cana import PRECIO as PRECIO_CANA
from ..cana import Cana
from ..carnet import PRECIO as PRECIO_CARNET
from ..carnet import Carnet
from ..churros import PRECIO as PRECIO_CHURROS
from ..churros import Churros
from ..cine import PRECIO as PRECIO_CINE
from ..cine import Cine
from ..coche import PRECIO as PRECIO_COCHE
from ..coche import Coche
from ..concierto import PRECIO as PRECIO_CONCIERTO
from ..concierto import Concierto
from ..croquetas import PRECIO as PRECIO_CROQUETAS
from ..croquetas import Croquetas
from ..emoji import cara as cara_emoji
from ..equivale import COSAS as COSAS_EQUIVALE
from ..futbol import PRECIO as PRECIO_FUTBOL
from ..futbol import Futbol
from ..gasolina import DEPOSITO, Gasolina
from ..gasolina import PRECIO as PRECIO_GASOLINA
from ..gimnasio import PRECIO as PRECIO_GIMNASIO
from ..gimnasio import Gimnasio
from ..hotel import PRECIO as PRECIO_HOTEL
from ..hotel import Hotel
from ..iphone import PRECIO as PRECIO_IPHONE
from ..iphone import Iphone
from ..jamon import PRECIO as PRECIO_JAMON
from ..jamon import Jamon
from ..kebab import PRECIO as PRECIO_KEBAB
from ..kebab import Kebab
from ..lambo import PRECIO as PRECIO_LAMBO
from ..lambo import Lambo
from ..libro import PRECIO as PRECIO_LIBRO
from ..libro import Libro
from ..loteria import PRECIO as PRECIO_LOTERIA
from ..loteria import Loteria
from ..luz import PRECIO as PRECIO_LUZ
from ..luz import Luz
from ..macbook import PRECIO as PRECIO_MACBOOK
from ..macbook import Macbook
from ..menu import PRECIO as PRECIO_MENU
from ..menu import Menu
from ..metro import PRECIO as PRECIO_METRO
from ..metro import Metro
from ..navidad import PRECIO as PRECIO_NAVIDAD
from ..navidad import Navidad
from ..netflix import PRECIO as PRECIO_NETFLIX
from ..netflix import Netflix
from ..nochevieja import PRECIO as PRECIO_CAVA
from ..nochevieja import Nochevieja
from ..oro import Oro
from ..paella import PRECIO as PRECIO_PAELLA
from ..paella import Paella
from ..pan import PRECIO as PRECIO_PAN
from ..pan import Pan
from ..peluqueria import PRECIO as PRECIO_PELUQUERIA
from ..peluqueria import Peluqueria
from ..piso import METROS as METROS_PISO
from ..piso import PRECIO as PRECIO_PISO
from ..piso import Piso
from ..ps5 import PRECIO as PRECIO_PS5
from ..ps5 import Ps5
from ..rolex import PRECIO as PRECIO_ROLEX
from ..rolex import Rolex
from ..sofa import PRECIO as PRECIO_SOFA
from ..sofa import Sofa
from ..spotify import PRECIO as PRECIO_SPOTIFY
from ..spotify import Spotify
from ..sueldo import PAGA as PAGA_SMI
from ..sueldo import Sueldo
from ..supermercado import PRECIO as PRECIO_SUPER
from ..supermercado import Super
from ..switch import PRECIO as PRECIO_SWITCH
from ..switch import Switch
from ..taxi import PRECIO as PRECIO_TAXI
from ..taxi import Taxi
from ..telegram import escape
from ..tesla import PRECIO as PRECIO_TESLA
from ..tesla import Tesla
from ..tiempo import parte as parte_tiempo
from ..tortilla import PRECIO as PRECIO_TORTILLA
from ..tortilla import Tortilla
from ..videojuego import PRECIO as PRECIO_VIDEOJUEGO
from ..videojuego import Videojuego
from ..vuelo import PRECIO as PRECIO_VUELO
from ..vuelo import Vuelo
from ..zapatillas import PRECIO as PRECIO_ZAPATILLAS
from ..zapatillas import Zapatillas
from .base import SIMBOLOS, _es, _num


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


def formatear_equivale(pedido: str = "") -> str:
    """Lo que sale con /equivale a secas o con algo que no tengo."""
    texto = []
    if pedido.strip():
        texto.append(f"No tengo «{escape(pedido.strip())}» 🤷")
    texto.append("🧮 <b>¿En qué quieres ver tu cartera?</b>")
    texto.append("Escribe /equivale y una de estas:")
    texto.append(", ".join(COSAS_EQUIVALE))
    texto.append("\nEj: <code>/equivale cañas</code>")
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
