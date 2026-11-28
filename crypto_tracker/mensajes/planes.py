"""Los mensajes de objetivos, planes de compra y metas."""

from datetime import date, datetime

from ..informes.mes import MESES
from ..inversion.apy import Tramo
from ..inversion.limite import Limite
from ..inversion.meta import Meta
from ..inversion.movimientos import texto_cantidad
from ..inversion.objetivo import Escenario
from ..inversion.plan import MAX_AÑOS as MAX_AÑOS_PLAN
from ..inversion.plan import TEXTO as TEXTO_PLAN
from ..inversion.plan import Camino
from ..inversion.plan import cuanto as cuanto_plan
from ..inversion.posicion import Entrada
from ..inversion.promediar import Promedio
from ..nucleo.telegram import escape
from ..rango import barra
from .base import SIMBOLOS, _barra_progreso, _es, _flecha, _ganancia, _hace, _num


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


def formatear_promediar(p: Promedio, currency: str) -> str:
    """Respuesta de /promediar."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    nombre = escape(p.coin_id.replace("-", " ").title())
    medio = f"{simbolo}{_num(p.medio)}"
    objetivo = f"{simbolo}{_num(p.objetivo)}"
    ahora = f"{simbolo}{_num(p.precio)}"

    if p.ya_esta:
        return (
            f"🟢 <b>{nombre}</b> ya te sale a {medio}, que no pasa de {objetivo}. "
            "No te hace falta comprar más."
        )
    if p.imposible:
        return (
            f"🔴 <b>{nombre}</b> está a {ahora}: comprando a ese precio, tu medio "
            f"baja hacia ahí pero nunca de ahí. Pide uno entre {ahora} y {medio}."
        )

    despues = p.cantidad + p.comprar
    return (
        f"⚖️ <b>Para que {nombre} te salga a {objetivo}</b>\n\n"
        f"Compra <b>{texto_cantidad(p.comprar)} {nombre}</b> por "
        f"<b>{simbolo}{_num(p.dinero)}</b> al precio de ahora ({ahora})\n"
        f"<i>Tienes {texto_cantidad(p.cantidad)} a {medio} de media; después "
        f"tendrías {texto_cantidad(despues)} a {objetivo}. Sin comisiones.</i>"
    )


def formatear_posicion(e: Entrada, currency: str) -> str:
    """Respuesta de /posicion."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    capital = f"{simbolo}{_num(e.capital)}"
    riesgo = f"{e.riesgo:g}".replace(".", ",")
    stop = f"-{e.stop:.2f}".rstrip("0").rstrip(".").replace(".", ",")

    texto = ["📐 <b>Cuánto meter</b>", ""]
    if e.todo:
        real = f"{e.perdida / e.capital * 100:.2f}".rstrip("0").rstrip(".")
        texto.append(
            f"Con el stop tan cerca ({stop}%) puedes meter los <b>{capital}</b> "
            f"enteros: si salta, pierdes {simbolo}{_num(e.perdida)}, un "
            f"{real.replace('.', ',')}%, dentro del {riesgo}% que aceptas"
        )
    else:
        texto.append(
            f"Con {capital} y aceptando perder un {riesgo}%, mete "
            f"<b>{simbolo}{_num(e.dinero)}</b>"
        )
        texto.append(
            f"Si salta el stop ({stop}%), pierdes {simbolo}{_num(e.perdida)} y no más"
        )

    if e.coin_id and e.cantidad is not None:
        nombre = escape(e.coin_id.replace("-", " ").title())
        texto.append(
            f"\nSon <b>{texto_cantidad(e.cantidad)} {nombre}</b> a "
            f"{simbolo}{_num(e.precio)}; el stop, a "
            f"<b>{simbolo}{_num(e.precio_stop)}</b>"
        )
    texto.append("<i>Sin contar comisiones ni que el stop salte algo más abajo</i>")
    return "\n".join(texto)


def formatear_plan(c: Camino, currency: str, hoy: date) -> str:
    """Respuesta de /plan."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    p = c.peticion
    meta = f"{simbolo}{_num(p.meta)}"
    if c.veces == 0:
        return f"🎉 Ya está: tu cartera vale {simbolo}{_num(c.inicio)}, más que {meta}"

    aporte = f"{simbolo}{_num(p.aporte)} {TEXTO_PLAN[p.frecuencia]}"
    anual = f"{p.anual:g}".replace(".", ",")
    if c.veces is None:
        texto = [f"🐌 Con {aporte} no llegas a {meta} ni en {MAX_AÑOS_PLAN} años"]
        if p.anual < 0:
            perdida = f"{-p.anual:g}".replace(".", ",")
            texto.append(f"Perdiendo un {perdida}% al año, se come lo que metes")
        else:
            texto.append("Mete algo más o apunta a una cifra más baja")
        return "\n".join(texto)

    fecha = c.fecha(hoy)
    texto = [
        f"🗓️ <b>Hacia {meta}</b>",
        "",
        f"Metiendo {aporte}, llegas en <b>{cuanto_plan(c.dias)}</b>, "
        f"hacia {MESES[fecha.month - 1]} de {fecha.year}",
    ]
    linea = f"Habrás metido {simbolo}{_num(c.metido)}"
    if p.anual and abs(c.intereses) >= 0.01:
        signo = "pone" if c.intereses > 0 else "quita"
        linea += f" y el {anual}% al año {signo} {simbolo}{_num(abs(c.intereses))}"
    texto.append(linea)
    if c.inicio:
        texto.append(f"Contando los {simbolo}{_num(c.inicio)} que ya tienes en cartera")
    if p.anual:
        texto.append(
            "<i>Lo del % al año es suponer mucho: la cripto no va en línea recta</i>"
        )
    return "\n".join(texto)


def formatear_apy(
    unidad: str,
    cantidad: float,
    apy: float,
    tramos: list[Tramo],
    precio: float | None,
    currency: str,
    de_cartera: bool = False,
) -> str:
    """Respuesta de /apy. unidad es ETH, o el nombre si no tiene símbolo conocido."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    unidad = escape(unidad)
    pct = f"{apy:g}".replace(".", ",")
    tuyos = " (lo de tu cartera)" if de_cartera else ""
    texto = [
        f"🌱 <b>{texto_cantidad(cantidad)} {unidad} al {pct}% al año</b>{tuyos}",
        "",
    ]
    for t in tramos:
        años = "1 año" if t.años == 1 else f"{t.años} años"
        linea = (
            f"En {años}: <b>{_cifras(t.cantidad)} {unidad}</b> (+{_cifras(t.ganado)})"
        )
        if precio:
            linea += f" · {simbolo}{_num(t.cantidad * precio)}"
        texto.append(linea)

    if precio:
        texto.append(
            f"\n<i>A {simbolo}{_num(precio)}, el precio de hoy. Lo que gana el "
            "staking es en cripto: si el precio baja, puedes tener más y que "
            "valga menos</i>"
        )
    return "\n".join(texto)


def _cifras(cantidad: float) -> str:
    # Con 8 decimales, 2,96048857 ETH; para hacerse una idea sobra con 6 cifras.
    return texto_cantidad(float(f"{cantidad:.6g}"))


def formatear_limite(
    lim: Limite, currency: str, hoy: date, puesto: bool = False
) -> str:
    """Respuesta de /limite. Con puesto, es que se acaba de poner."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    mes = MESES[hoy.month - 1]
    texto = ["✅ Hecho, te aviso al comprar si te pasas", ""] if puesto else []
    texto += [
        f"🧮 <b>Tu límite: {simbolo}{_num(lim.limite)} al mes</b>",
        f"En {mes} llevas {simbolo}{_num(lim.gastado)} en compras",
        _barra_progreso(min(lim.hecho, 100)),
    ]
    if lim.pasado:
        texto.append(f"⚠️ Te has pasado {simbolo}{_num(-lim.falta)}")
    else:
        texto.append(f"Te quedan {simbolo}{_num(lim.falta)} hasta fin de mes")
    texto.append("<i>/limite no lo quita</i>")
    return "\n".join(texto)


def linea_limite(lim: Limite, currency: str) -> str | None:
    """Lo que se añade a /compra si te pasas o te acercas. None si vas bien."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    if lim.pasado:
        return (
            f"⚠️ Con esta, este mes llevas <b>{simbolo}{_num(lim.gastado)}</b> en "
            f"compras: {simbolo}{_num(-lim.falta)} por encima de tu límite de "
            f"{simbolo}{_num(lim.limite)}"
        )
    if lim.cerca:
        return (
            f"🧮 Llevas {simbolo}{_num(lim.gastado)} de tus "
            f"{simbolo}{_num(lim.limite)} de este mes: te quedan "
            f"{simbolo}{_num(lim.falta)}"
        )
    return None


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
