"""La página del panel. Los datos vienen hechos de panel.py."""

import json
from datetime import date, datetime
from html import escape
from urllib.parse import parse_qs, quote, urlencode, urlsplit

from . import impuestos, miedo, version
from .mensajes.base import SIMBOLOS, _num, describir
from .mes import MESES
from .panel import (
    PUNTOS_GRAFICA,
    Alerta,
    Dia,
    Fila,
    Panel,
    Vigilada,
    cambio,
    en_bitcoin,
    hace,
    muestrear,
    trazo,
)
from .recordar import DIAS

# Cada cuánto se refresca sola, en segundos. Los precios no cambian más rápido.
REFRESCO = 60

ANCHO, ALTO = 600, 180
MINI_ANCHO, MINI_ALTO = 100, 28


def _nombre(coin_id: str) -> str:
    return escape(coin_id.replace("-", " ").title())


def _importe(valor: float | None, moneda: str) -> str:
    if valor is None:
        return "—"
    simbolo = SIMBOLOS.get(moneda, moneda.upper() + " ")
    signo = "-" if valor < 0 else ""
    return f"{signo}{simbolo}{_num(abs(valor))}"


def _enlace(coin_id: str) -> str:
    # Los ids son los de CoinGecko, así que la página de cada una sale directa.
    url = f"https://www.coingecko.com/es/monedas/{quote(coin_id)}"
    return (
        f'<a class="moneda" href="{url}" target="_blank" rel="noopener">'
        f"{_nombre(coin_id)}</a>"
    )


def _dinero(valor: float | None, moneda: str) -> str:
    # El span es para el botón de ocultar cifras. Los precios de mercado van con
    # _importe: no dicen nada de lo que tienes.
    if valor is None:
        return "—"
    return f'<span class="dinero">{_importe(valor, moneda)}</span>'


def _pct(valor: float | None, signo: bool = True) -> str:
    if valor is None:
        return "—"
    texto = f"{valor:+.2f}" if signo else f"{valor:.1f}"
    return texto.replace(".", ",") + " %"


def _tono(valor: float | None) -> str:
    if valor is None or abs(valor) < 0.005:
        return "neutro"
    return "sube" if valor > 0 else "baja"


def _cantidad(valor: float) -> str:
    # Las cantidades no son dinero: 0,1 BTC, no 0,10.
    texto = f"{valor:,.8f}".rstrip("0").rstrip(".")
    return texto.replace(",", "@").replace(".", ",").replace("@", ".")


def _mini(linea: list[float], tono: str) -> str:
    d = trazo(linea, MINI_ANCHO, MINI_ALTO)
    if not d:
        # Una raya punteada en vez del texto: repetido en cada fila ensuciaba.
        return (
            f'<svg class="mini mini--vacia" viewBox="0 0 {MINI_ANCHO} {MINI_ALTO}" '
            'preserveAspectRatio="none" role="img" aria-label="sin histórico">'
            f'<title>sin histórico</title><path d="M0,{MINI_ALTO / 2} '
            f'H{MINI_ANCHO}" vector-effect="non-scaling-stroke"/></svg>'
        )
    return (
        f'<svg class="mini mini--{tono}" viewBox="0 0 {MINI_ANCHO} {MINI_ALTO}" '
        f'preserveAspectRatio="none" aria-hidden="true">'
        f'<path d="{d}" vector-effect="non-scaling-stroke"/></svg>'
    )


def _cuando(p: Panel, ahora: datetime) -> str:
    texto = hace(p.actualizado, ahora)
    if p.actualizado is None:
        return texto
    local = p.actualizado.astimezone()
    exacta = f"{DIAS[local.weekday()]} {local:%d/%m} a las {local:%H:%M:%S}"
    # En el móvil no hay ratón que enseñe el title: allí va la hora a la vista.
    return (
        f'<time datetime="{local.isoformat()}" title="{exacta}">{texto}</time>'
        f'<span class="estado__hora"> · {local:%d/%m %H:%M}</span>'
    )


def resumen(p: Panel, ahora: datetime, oculto: bool) -> str:
    """El texto para pegar en WhatsApp. Oculto: solo porcentajes, sin cifras."""
    lineas = [f"*Mi cartera* · {ahora.astimezone():%d/%m}"]
    if p.ganancia is not None:
        desde = f"{_pct(p.porcentaje)} desde que compré"
        if oculto:
            lineas.append(desde)
        else:
            total = _importe(p.total, p.moneda)
            lineas.append(f"{total} · {_importe(p.ganancia, p.moneda)} ({desde})")
    elif not oculto:
        lineas.append(_importe(p.total, p.moneda))
    if p.cambio_24h is not None:
        lineas.append(f"En 24 h: {_pct(p.cambio_24h)}")
    lineas.append("")
    for f in p.filas:
        nombre = f.coin_id.replace("-", " ").title()
        peso = _pct(f.peso, signo=False)
        if oculto:
            lineas.append(f"{nombre}: {peso} del total")
        else:
            lineas.append(f"{nombre}: {_importe(f.valor, p.moneda)} ({peso})")
    return "\n".join(lineas)


def avisos_navegador(p: Panel) -> list[dict]:
    """Los avisos que ha mandado el bot, para que el JS saque los nuevos."""
    lista = []
    for coin_id, a in sorted(p.avisos.items(), key=lambda par: par[1].cuando):
        hora = a.cuando.astimezone()
        verbo = "Ha subido" if a.sube else "Ha bajado"
        flecha = "🔺" if a.sube else "🔻"
        lista.append(
            {
                "id": f"{coin_id}@{a.cuando.isoformat()}",
                "titulo": f"{flecha} {coin_id.replace('-', ' ').title()}",
                "texto": f"{verbo} a {_importe(a.precio, p.moneda)} ({hora:%H:%M})",
            }
        )
    return lista


def _copiar(p: Panel, ahora: datetime) -> str:
    if p.total is None:
        return ""
    # Los dos textos van ya hechos: el JS solo elige según tengas las cifras tapadas.
    return (
        '<button class="copiar" type="button" title="Copiar resumen"'
        f' data-texto="{escape(resumen(p, ahora, False))}"'
        f' data-oculto="{escape(resumen(p, ahora, True))}">📋</button>'
    )


def _cabecera(p: Panel, ahora: datetime, parado: bool) -> str:
    estado = "parado" if parado else "vivo"
    cuando = _cuando(p, ahora)
    avisos = escape(json.dumps(avisos_navegador(p), ensure_ascii=False))
    aviso = (
        '<span class="estado__texto">El bot no guarda precios desde '
        f"{cuando}. ¿Está encendido?</span>"
        if parado
        else f'<span class="estado__texto">Actualizado {cuando}</span>'
    )
    if p.total is None:
        grande = '<p class="total total--vacio">Sin cartera</p>'
        detalle = (
            '<p class="detalle">Apunta lo que tienes con <code>/compra</code> o en '
            "<code>PORTFOLIO</code> del <code>.env</code>.</p>"
        )
    else:
        grande = f'<p class="total" data-k="total">{_dinero(p.total, p.moneda)}</p>'
        partes = []
        if p.ganancia is not None:
            t = _tono(p.ganancia)
            partes.append(
                f'<span class="pastilla pastilla--{t}" data-k="ganancia">'
                f"{_dinero(p.ganancia, p.moneda)} · {_pct(p.porcentaje)}</span>"
                '<span class="detalle__nota">desde que compraste</span>'
            )
        if p.cambio_24h is not None:
            t = _tono(p.cambio_24h)
            partes.append(
                f'<span class="pastilla pastilla--{t}" data-k="cambio">'
                f"{_pct(p.cambio_24h)}</span>"
                '<span class="detalle__nota">en 24 h</span>'
            )
        detalle = f'<p class="detalle">{"".join(partes)}</p>' if partes else ""

    return f"""
<header class="cabecera seccion" style="--i:0" data-avisos="{avisos}">
  <div class="cabecera__fila">
    <span class="marca">CryptoPriceTracker</span>
    <span class="cabecera__lado">
      <button class="estado estado--{estado}" type="button"
              title="Actualizar ahora (R)">
        <span class="estado__punto"></span>{aviso}
      </button>
      <span class="botones">
        <button class="campana" type="button" aria-pressed="false" hidden>🔕</button>
        {_copiar(p, ahora)}
        <button class="ojo" type="button" aria-pressed="false"
                title="Ocultar cifras (O)">👁</button>
      </span>
    </span>
  </div>
  <p class="etiqueta">Tu cartera</p>
  {grande}
  {detalle}
  {_animo(p)}
</header>"""


def matiz(valor: int) -> int:
    """El tono del fondo: de rojo con miedo extremo (0) a verde con codicia
    extrema (100), pasando por el ámbar."""
    return round(valor * 1.4)


def _animo(p: Panel) -> str:
    if p.miedo is None:
        return ""
    emoji, nombre = miedo.nombre(p.miedo)
    return (
        '<p class="animo" title="Índice de miedo y codicia de alternative.me">'
        f'<span class="animo__punto"></span>Mercado: {emoji} {escape(nombre)} · '
        f"{p.miedo.valor}/100</p>"
    )


def _fondo(p: Panel) -> str:
    if p.miedo is None:
        return ""
    return f' class="con-animo" style="--animo:{matiz(p.miedo.valor)}"'


def _altura(v: float, escala: tuple[float, float]) -> float:
    """En % desde arriba, con la misma cuenta que trazo()."""
    suelo, techo = escala
    return round(100 - (v - suelo) / (techo - suelo) * 100, 1) if techo > suelo else 50


def _pico(
    valores: list[float], i: int, arriba: bool, moneda: str, escala: tuple
) -> str:
    x = i / (len(valores) - 1) * 100
    clase = "pico" if arriba else "pico pico--abajo"
    # El desplazamiento va con x: en el borde izquierdo la cifra queda a la
    # derecha del punto y en el derecho a la izquierda, sin salirse nunca.
    return (
        f'<span class="{clase}" style="left:{x:.1f}%;--x:{x:.1f}%;'
        f'top:{_altura(valores[i], escala)}%">'
        f'<span class="pico__cifra">{_dinero(valores[i], moneda)}</span></span>'
    )


CURSOR = (
    '<span class="cursor"></span><span class="cursor__punto"></span>'
    '<span class="cursor__texto"></span>'
)


def _picos(valores: list[float], moneda: str, escala: tuple | None = None) -> str:
    alto, bajo = max(valores), min(valores)
    escala = escala or (bajo, alto)
    if alto == bajo:
        punto = _pico(valores, 0, True, moneda, escala)
        return (
            f'<div class="grafica__picos grafica__picos--plana">{punto}{CURSOR}</div>'
        )
    puntos = _pico(valores, valores.index(alto), True, moneda, escala) + _pico(
        valores, valores.index(bajo), False, moneda, escala
    )
    return f'<div class="grafica__picos">{puntos}{CURSOR}</div>'


def puntos_cursor(
    puntos: list[tuple[datetime, float]],
    moneda: str,
    escala: tuple[float, float] | None = None,
    btc: list[float] | None = None,
) -> list:
    """Para el JS de la gráfica: [hora, cifra, altura en %, en bitcoin] de cada
    punto. Lo de bitcoin va a None si no hay esa línea."""
    valores = [v for _, v in puntos]
    escala = escala or (min(valores), max(valores))
    return [
        [
            f"{t.astimezone():%d/%m %H:%M}",
            _importe(v, moneda),
            _altura(v, escala),
            _importe(btc[i], moneda) if btc else None,
        ]
        for i, (t, v) in enumerate(puntos)
    ]


def _leyenda(valores: list[float], btc: list[float], desde, moneda: str) -> str:
    diferencia = btc[-1] - valores[-1]
    if abs(diferencia) < 0.005:
        cuanto = "lo mismo que tienes"
    else:
        lado = "más" if diferencia > 0 else "menos"
        cuanto = f"{_dinero(abs(diferencia), moneda)} {lado} de lo que tienes"
    return (
        '<p class="grafica__leyenda">'
        '<span class="leyenda leyenda--tuya">Tu cartera</span>'
        '<span class="leyenda leyenda--btc">'
        f"Todo en bitcoin desde el {desde:%d/%m}: {_dinero(btc[-1], moneda)}, "
        f"{cuanto}</span></p>"
    )


def _grafica(p: Panel) -> str:
    if len(p.serie) < 2:
        cuerpo = (
            '<p class="vacio">Aún no hay precios suficientes para dibujarla. '
            "Vuelve cuando el bot lleve un rato guardando.</p>"
        )
        return _tarjeta("Los últimos 7 días", cuerpo, 1, "grafica")

    puntos = muestrear(p.serie, PUNTOS_GRAFICA)
    valores = [v for _, v in puntos]
    # Si solo tienes bitcoin, las dos líneas serían la misma.
    solo_btc = all(f.coin_id == "bitcoin" for f in p.filas)
    btc = [] if solo_btc else en_bitcoin(puntos, p.serie_btc)
    # Una sola escala para las dos, o no se podrían comparar a ojo.
    escala = (min(valores + btc), max(valores + btc))
    linea = trazo(valores, ANCHO, ALTO, escala)
    area = f"{linea} L{ANCHO},{ALTO} L0,{ALTO} Z"
    linea_btc = (
        f'<path class="grafica__btc" d="{trazo(btc, ANCHO, ALTO, escala)}" '
        'vector-effect="non-scaling-stroke"/>'
        if btc
        else ""
    )
    tono = _tono(valores[-1] - valores[0])
    desde, hasta = puntos[0][0].astimezone(), puntos[-1][0].astimezone()
    datos = escape(
        json.dumps(puntos_cursor(puntos, p.moneda, escala, btc), ensure_ascii=False)
    )
    leyenda = _leyenda(valores, btc, desde, p.moneda) if btc else ""

    cuerpo = f"""
<div class="grafica grafica--{tono}">
  <div class="grafica__zona" data-puntos="{datos}">
  {_picos(valores, p.moneda, escala)}
  <svg viewBox="0 0 {ANCHO} {ALTO}" preserveAspectRatio="none" role="img"
       aria-label="Lo que ha valido tu cartera en los últimos días">
    <defs>
      <linearGradient id="relleno" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" class="grafica__luz"/>
        <stop offset="1" class="grafica__sombra"/>
      </linearGradient>
      <clipPath id="corte"><rect class="grafica__corte" width="{ANCHO}"
        height="{ALTO + 20}" y="-10"/></clipPath>
    </defs>
    <g clip-path="url(#corte)">
      <path class="grafica__area" d="{area}"/>
      {linea_btc}
      <path class="grafica__linea" d="{linea}" vector-effect="non-scaling-stroke"/>
    </g>
  </svg>
  </div>
  <div class="grafica__fechas">
    <span>{desde:%d/%m %H:%M}</span>
    <button class="repetir" type="button">▶ Ver cómo fue</button>
    <span>{hasta:%d/%m %H:%M}</span>
  </div>
  {leyenda}
</div>"""
    semana = cambio(p.serie[-1][1], p.serie[0][1])
    titulo = "Los últimos 7 días"
    if semana is not None:
        titulo += (
            f' · <span class="h2__cambio num--{_tono(semana)}">{_pct(semana)}</span>'
        )
    return _tarjeta(titulo, cuerpo, 1, "grafica")


def _fila(f: Fila, moneda: str) -> str:
    tono = _tono(f.porcentaje)
    ganancia = (
        f'<span class="num num--{tono} ganancia">{_dinero(f.ganancia, moneda)}'
        f"<small>{_pct(f.porcentaje)}</small></span>"
        if f.ganancia is not None
        else '<span class="num num--neutro ganancia">—<small>sin coste</small></span>'
    )
    return f"""
<li class="fila">
  <div class="fila__nombre">
    <strong>{_enlace(f.coin_id)}</strong>
    <small><span class="dinero">{_cantidad(f.cantidad)}</span> ·
      {_importe(f.precio, moneda)}</small>
  </div>
  {_mini(f.linea, _tono(f.cambio_24h))}
  <span class="num" data-k="v-{escape(f.coin_id)}">{_dinero(f.valor, moneda)}
    <small class="num--{_tono(f.cambio_24h)}">{_pct(f.cambio_24h)} 24 h</small></span>
  {ganancia}
  <div class="peso">
    <div class="peso__barra"><span style="width:{f.peso:.1f}%"></span></div>
    <small>{_pct(f.peso, signo=False)} del total</small>
  </div>
</li>"""


def _fila_total(p: Panel) -> str:
    invertido = (
        f"<small>invertido {_dinero(p.invertido, p.moneda)}</small>"
        if p.invertido is not None
        else ""
    )
    tono = _tono(p.porcentaje)
    ganancia = (
        f'<span class="num num--{tono} ganancia">{_dinero(p.ganancia, p.moneda)}'
        f"<small>{_pct(p.porcentaje)}</small></span>"
        if p.ganancia is not None
        else '<span class="num num--neutro ganancia">—</span>'
    )
    return f"""
<li class="fila fila--total">
  <div class="fila__nombre"><strong>Total</strong>{invertido}</div>
  <span class="mini"></span>
  <span class="num">{_dinero(p.total, p.moneda)}
    <small class="num--{_tono(p.cambio_24h)}">{_pct(p.cambio_24h)} 24 h</small></span>
  {ganancia}
</li>"""


def _cartera(p: Panel) -> str:
    if not p.filas:
        return ""
    filas = "".join(_fila(f, p.moneda) for f in p.filas)
    # Con una sola cripto el total sería la misma fila repetida.
    if len(p.filas) > 1:
        filas += _fila_total(p)
    faltan = ""
    if p.faltan:
        nombres = ", ".join(_nombre(c) for c in p.faltan)
        faltan = f'<p class="nota">Sin precio guardado todavía: {nombres}.</p>'
    cuerpo = f'<ul class="lista lista--cartera">{filas}</ul>{faltan}'
    return _tarjeta(f"Lo que tienes{_cuenta(len(p.filas))}", cuerpo, 2, "ancha")


def _vigilada(v: Vigilada, moneda: str) -> str:
    tono = _tono(v.cambio_24h)
    return f"""
<li class="fila fila--corta">
  <div class="fila__nombre">
    <strong>{_enlace(v.coin_id)}</strong>
    <small>{escape(describir(v.watch, moneda))}</small>
  </div>
  {_mini(v.linea, tono)}
  <span class="num" data-k="p-{escape(v.coin_id)}">{_importe(v.precio, moneda)}
    <small class="num--{tono}">{_pct(v.cambio_24h)}</small></span>
</li>"""


def _vigiladas(p: Panel) -> str:
    if not p.vigiladas:
        cuerpo = '<p class="vacio">No vigilas ninguna. Prueba con /vigilar btc 5%</p>'
    else:
        filas = "".join(_vigilada(v, p.moneda) for v in p.vigiladas)
        cuerpo = f'<ul class="lista">{filas}</ul>'
    return _tarjeta(f"Lo que vigilo{_cuenta(len(p.vigiladas))}", cuerpo, 3)


def _alerta(a: Alerta, moneda: str, cerca: bool = False) -> str:
    flecha = "↑" if a.sube else "↓"
    nombre = "Tu cartera" if a.coin_id == "cartera" else _nombre(a.coin_id)
    # Sin rojo ni verde: que falte un 5 % no es ni bueno ni malo.
    if a.alcanzada:
        falta = (
            '<span class="num num--listo">Ya está'
            "<small>sale en el próximo aviso</small></span>"
        )
    elif a.falta is not None:
        falta = (
            f'<span class="num">{_pct(abs(a.falta), signo=False)}'
            f"<small>le falta {'subir' if a.sube else 'bajar'}</small></span>"
        )
    else:
        falta = '<span class="num num--neutro">—<small>sin precio</small></span>'

    nota = f"<small>📝 {escape(a.nota)}</small>" if a.nota else ""
    clase = "fila fila--alerta fila--cerca" if cerca else "fila fila--alerta"
    aviso = ' · <span class="cerca">la más cerca</span>' if cerca else ""
    return f"""
<li class="{clase}">
  <div class="fila__nombre">
    <strong>{nombre} <span class="flecha">{flecha}</span>
      {_importe(a.objetivo, moneda)}</strong>
    <small>#{a.id} · ahora {_importe(a.precio, moneda)}{aviso}</small>{nota}
  </div>
  {falta}
</li>"""


def _alertas(p: Panel) -> str:
    if not p.alertas:
        cuerpo = (
            '<p class="vacio">No tienes alertas puestas. '
            "Con /alerta btc 70000 te aviso una vez al llegar.</p>"
        )
    else:
        # Ya vienen ordenadas por lo que les falta. Las que ya han llegado tienen
        # su propio "Ya está", y con una sola no hay nada que comparar.
        pendientes = [a for a in p.alertas if a.falta is not None and not a.alcanzada]
        cerca = pendientes[0] if len(p.alertas) > 1 and pendientes else None
        filas = "".join(_alerta(a, p.moneda, a is cerca) for a in p.alertas)
        cuerpo = f'<ul class="lista">{filas}</ul>'
    return _tarjeta(f"Alertas pendientes{_cuenta(len(p.alertas))}", cuerpo, 4)


def _titulo(p: Panel) -> str:
    if p.total is None:
        return "Tu cartera · CryptoPriceTracker"
    titulo = _importe(p.total, p.moneda)
    if p.cambio_24h is not None:
        titulo += f" · {_pct(p.cambio_24h)}"
    return escape(titulo)


# Los mismos que --sube, --baja, --acento y --aviso del modo claro. No llegan las
# variables CSS: el icono es una imagen aparte.
ICONO_COLOR = {
    "sube": "#0f9f6e",
    "baja": "#e0445a",
    "neutro": "#6d4aff",
    "parado": "#d48a00",
}
ICONO_TRAZO = {
    "sube": "M7 22 L13 15 L18 19 L25 10",
    "baja": "M7 10 L13 17 L18 13 L25 22",
    "neutro": "M7 16 H25",
    # Una exclamación: el punto es una raya de nada con la punta redonda.
    "parado": "M16 8 V18 M16 24 V24.01",
}


def _icono(p: Panel, parado: bool) -> str:
    # Parado manda: un verde de hace cinco días engaña más que no saber nada.
    tono = "parado" if parado else _tono(p.cambio_24h)
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
        f"<rect width='32' height='32' rx='8' fill='{ICONO_COLOR[tono]}'/>"
        f"<path d='{ICONO_TRAZO[tono]}' fill='none' stroke='white' "
        "stroke-width='3.5' stroke-linecap='round' stroke-linejoin='round'/></svg>"
    )
    return "data:image/svg+xml," + quote(svg)


def _cuenta(n: int) -> str:
    # Con cero no: la tarjeta ya lo dice con su texto de vacío.
    return f' <span class="h2__cuenta">{n}</span>' if n else ""


def _tarjeta(titulo: str, cuerpo: str, orden: int, clase: str = "") -> str:
    extra = f" tarjeta--{clase}" if clase else ""
    return f"""
<section class="tarjeta seccion{extra}" style="--i:{orden}">
  <h2>{titulo}</h2>
  {cuerpo}
</section>"""


# Por debajo de esto el día cuenta como plano: un 0,01 % en verde parece un fallo.
IGUAL = 0.05
# Hasta dónde llega cada intensidad de color, en % de lo que se movió el día.
NIVELES = (1, 3, 6)


def nivel(cambio: float | None) -> str:
    """La clase de la casilla: sube-1 a sube-4, baja-1 a baja-4, igual o vacía."""
    if cambio is None:
        return "vacia"
    if abs(cambio) < IGUAL:
        return "igual"
    fuerza = 1 + sum(abs(cambio) >= n for n in NIVELES)
    return f"{'sube' if cambio > 0 else 'baja'}-{fuerza}"


def _casilla(d: Dia, hoy: date) -> str:
    if d.dia > hoy:
        return '<span class="cal__dia cal__dia--futuro"></span>'
    # Sin la cifra en euros: el 👁 no llega a los title y esto se ve con el ratón.
    cuando = f"{DIAS[d.dia.weekday()]} {d.dia:%d/%m}"
    texto = f"{cuando}: {_pct(d.cambio)}" if d.cambio is not None else cuando
    if d.cambio is None:
        texto += ": sin dato" if d.valor is None else ": primer día"
    clase = f"cal__dia cal__dia--{nivel(d.cambio)}"
    if d.dia == hoy:
        clase += " cal__dia--hoy"
    return f'<span class="{clase}" title="{texto}"></span>'


def _calendario(p: Panel, hoy: date) -> str:
    if not p.calendario:
        return ""
    semanas = len(p.calendario) // 7
    meses = "".join(
        f'<span style="grid-column:{i // 7 + 1}">{MESES[d.dia.month - 1][:3]}</span>'
        for i, d in enumerate(p.calendario)
        if d.dia.day == 1 or i == 0
    )
    casillas = "".join(_casilla(d, hoy) for d in p.calendario)
    con_dato = [d for d in p.calendario if d.cambio is not None]
    resumen = (
        '<p class="cal__resumen">Aún no hay dos días seguidos con el precio de '
        "todas tus criptos: en cuanto los haya, se irán coloreando.</p>"
    )
    if con_dato:
        verdes = sum(d.cambio >= IGUAL for d in con_dato)
        rojos = sum(d.cambio <= -IGUAL for d in con_dato)
        mejor = max(con_dato, key=lambda d: d.cambio)
        peor = min(con_dato, key=lambda d: d.cambio)
        resumen = (
            f'<p class="cal__resumen"><span class="num--sube">{verdes} en verde</span>'
            f' · <span class="num--baja">{rojos} en rojo</span>'
            f" · mejor el {mejor.dia:%d/%m}, {_pct(mejor.cambio)}"
            f" · peor el {peor.dia:%d/%m}, {_pct(peor.cambio)}</p>"
        )
    primero = next(d.dia for d in p.calendario if d.valor is not None)
    titulo = "Tu año, día a día" if (hoy - primero).days > 300 else "Día a día"
    cuerpo = f"""
<p class="nota cal__intro">Lo que hace cada día tu cartera de hoy, desde el
  {primero:%d/%m/%Y}. Cuanto más intenso, más se movió.</p>
<div class="cal__scroll">
  <div class="cal" style="--semanas:{semanas}">
    <div class="cal__meses">{meses}</div>
    <div class="cal__semana"><span>L</span><span></span><span>X</span><span></span>
      <span>V</span><span></span><span></span></div>
    <div class="cal__rejilla">{casillas}</div>
  </div>
</div>
<div class="cal__pie">
  {resumen}
  <p class="cal__escala"><span>baja</span>
    <span class="cal__dia cal__dia--baja-4"></span>
    <span class="cal__dia cal__dia--baja-2"></span>
    <span class="cal__dia cal__dia--igual"></span>
    <span class="cal__dia cal__dia--sube-2"></span>
    <span class="cal__dia cal__dia--sube-4"></span><span>sube</span></p>
</div>"""
    return _tarjeta(titulo, cuerpo, 2, "ancha")


# El deslizador va de ×0,2 a ×5: con una escala lineal, de -80 % a +400 %, casi
# todo el recorrido sería para subidas y las bajadas quedarían en un rincón.
SIM_TOPE = 5


def datos_simulador(p: Panel) -> dict:
    """Lo que necesita el JS del simulador, ya calculado aquí."""
    datos = {
        "simbolo": SIMBOLOS.get(p.moneda, p.moneda.upper() + " "),
        "tope": SIM_TOPE,
        "monedas": [
            {"id": f.coin_id, "cantidad": f.cantidad, "precio": f.precio}
            for f in p.filas
        ],
        "invertido": p.invertido,
        # Hacienda va en euros: en otra moneda la cuenta no valdría.
        "tramos": None,
    }
    if p.moneda == "eur":
        # El último tramo no tiene techo, y infinito no cabe en JSON.
        datos["tramos"] = [
            [None if hasta == float("inf") else hasta, tipo]
            for hasta, tipo in impuestos.TRAMOS
        ]
    return datos


def _simulador(p: Panel) -> str:
    if not p.filas:
        return ""

    def fila(id_: str, nombre: str, detalle: str) -> str:
        return f"""
<div class="sim__fila">
  <label for="sim-{escape(id_)}">
    <strong>{nombre}</strong><small>{detalle}</small>
  </label>
  <input type="range" id="sim-{escape(id_)}" data-id="{escape(id_)}"
         min="-1" max="1" step="0.01" value="0">
  <span class="sim__pct num">0 %</span>
  <span class="sim__precio num" data-precio="{escape(id_)}"></span>
</div>"""

    filas = fila("*", "Todas a la vez", "mueve todos los precios igual")
    filas += "".join(
        fila(f.coin_id, _nombre(f.coin_id), f"hoy {_importe(f.precio, p.moneda)}")
        for f in p.filas
    )
    datos = escape(json.dumps(datos_simulador(p)))
    hacienda = (
        """
  <div><small>Si lo vendieras todo, a Hacienda</small>
    <strong class="sim__hacienda num">—</strong>
    <small class="sim__tipo"></small></div>"""
        if p.moneda == "eur" and p.invertido is not None
        else ""
    )
    ganancia = (
        """
  <div><small>Ganancia desde que compraste</small>
    <strong class="sim__ganancia num">—</strong>
    <small class="sim__gpct"></small></div>"""
        if p.invertido is not None
        else ""
    )
    cuerpo = f"""
<p class="nota sim__intro">Mueve los precios y mira qué sería de tu cartera.
  Es solo una cuenta: no cambia nada.</p>
<div class="sim__filas">{filas}</div>
<div class="sim__resultado">
  <div><small>Tu cartera valdría</small>
    <strong class="sim__total num">—</strong><small class="sim__dif"></small></div>
  {ganancia}{hacienda}
</div>
<button class="sim__volver" type="button" hidden>Volver a los precios de hoy</button>"""
    return f"""
<section class="tarjeta seccion tarjeta--ancha simulador" style="--i:5"
         data-sim="{datos}">
  <h2>¿Y si…?</h2>
  {cuerpo}
</section>"""


def pagina(p: Panel, ahora: datetime, parado: bool) -> str:
    contenido = "".join(
        [
            _cabecera(p, ahora, parado),
            _grafica(p),
            _cartera(p),
            _calendario(p, ahora.astimezone().date()),
            _vigiladas(p),
            _alertas(p),
            _simulador(p),
        ]
    )
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f4f1fb" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0d0b16" media="(prefers-color-scheme: dark)">
<title>{_titulo(p)}</title>
<link rel="icon" href="{_icono(p, parado)}">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icono-180.png">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Cartera">
<script>{ANTES}</script>
<style>{CSS}</style>
</head>
<body{_fondo(p)}>
<main class="panel">{contenido}</main>
<footer class="pie">
  CryptoPriceTracker {escape(version.numero() or "")} · se actualiza sola cada minuto ·
  <a href="https://www.coingecko.com">Price data by CoinGecko</a>
</footer>
<script>{JS}</script>
</body>
</html>"""


# Ruido de SVG en una data URL, para la capa de grano del fondo.
GRANO = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' "
    "height='160'%3E%3Cfilter id='g'%3E%3CfeTurbulence type='fractalNoise' "
    "baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E"
    "%3Crect width='100%25' height='100%25' filter='url(%23g)'/%3E%3C/svg%3E"
)

CSS = """
:root {
  --fondo: #f4f1fb;
  --mancha-1: #c9b6ff;
  --mancha-2: #9fe3d1;
  --mancha-3: #ffc9a8;
  --texto: #1d1830;
  --suave: #6c6684;
  --cristal: rgba(255, 255, 255, 0.55);
  --borde: rgba(255, 255, 255, 0.7);
  --luz: rgba(255, 255, 255, 0.9);
  --linea-fila: rgba(29, 24, 48, 0.08);
  --acento: #6d4aff;
  --sube: #0f9f6e;
  --sube-fondo: rgba(15, 159, 110, 0.12);
  --baja: #e0445a;
  --baja-fondo: rgba(224, 68, 90, 0.12);
  --neutro-fondo: rgba(108, 102, 132, 0.12);
  --aviso: #d48a00;
  --sombra: 0 10px 40px -12px rgba(52, 32, 120, 0.25);
  --radio: 22px;
  --radio-chico: 999px;
  --suave-curva: cubic-bezier(0.22, 1, 0.36, 1);
  --muelle: cubic-bezier(0.34, 1.56, 0.64, 1);
  --rapido: 180ms;
  --lento: 700ms;
}

@media (prefers-color-scheme: dark) {
  :root {
    --fondo: #0d0b16;
    --mancha-1: #3b1f8f;
    --mancha-2: #0b5c4f;
    --mancha-3: #6b2a3c;
    --texto: #ece9f6;
    --suave: #9a94b4;
    --cristal: rgba(28, 24, 44, 0.55);
    --borde: rgba(255, 255, 255, 0.08);
    --luz: rgba(255, 255, 255, 0.18);
    --linea-fila: rgba(255, 255, 255, 0.07);
    --acento: #a48bff;
    --sube: #3fd6a0;
    --sube-fondo: rgba(63, 214, 160, 0.14);
    --baja: #ff6b81;
    --baja-fondo: rgba(255, 107, 129, 0.14);
    --neutro-fondo: rgba(154, 148, 180, 0.14);
    --aviso: #ffb648;
    --sombra: 0 14px 44px -10px rgba(0, 0, 0, 0.7);
  }
}

* { box-sizing: border-box; }

html { -webkit-text-size-adjust: 100%; }

body {
  margin: 0;
  min-height: 100vh;
  font: 15px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  color: var(--texto);
  background-color: var(--fondo);
  background-image:
    radial-gradient(40vw 40vw at 8% 0%, var(--mancha-1), transparent 70%),
    radial-gradient(35vw 35vw at 100% 30%, var(--mancha-2), transparent 70%),
    radial-gradient(45vw 45vw at 30% 110%, var(--mancha-3), transparent 70%);
  background-attachment: fixed;
}

/* Con el índice de miedo, la mancha de arriba toma su color. */
body.con-animo { --mancha-1: hsl(var(--animo) 85% 80%); }
@media (prefers-color-scheme: dark) {
  body.con-animo { --mancha-1: hsl(var(--animo) 55% 25%); }
}

.animo {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 14px 0 0;
  color: var(--suave);
  font-size: 13px;
}
.animo__punto {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: hsl(var(--animo) 75% 48%);
}

/* El grano: sin él, el degradado parece de plantilla. */
body::after {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.05;
  background-image: url("__GRANO__");
}

.panel {
  max-width: 1080px;
  margin: 0 auto;
  padding: 32px 16px 8px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.cabecera, .tarjeta--grafica, .tarjeta--ancha { grid-column: 1 / -1; }

.tarjeta, .cabecera {
  position: relative;
  padding: 22px 24px;
  border-radius: var(--radio);
  background: var(--cristal);
  border: 1px solid var(--borde);
  box-shadow: var(--sombra);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  backdrop-filter: blur(20px) saturate(180%);
}

/* La línea de luz de arriba, como un borde de vidrio. */
.tarjeta::before, .cabecera::before {
  content: "";
  position: absolute;
  top: 0;
  left: 24px;
  right: 24px;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--luz), transparent);
}

.seccion {
  animation: entra var(--lento) var(--suave-curva) both;
  animation-delay: calc(var(--i) * 70ms);
}

/* Al refrescar no se repite la entrada, solo late lo que cambia. */
.recargado .seccion { animation: none; }

@keyframes entra {
  from { opacity: 0; transform: translateY(14px) scale(0.99); }
}

h2 {
  margin: 0 0 14px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--suave);
}
.h2__cambio { font-weight: 700; }
.h2__cuenta {
  display: inline-block;
  min-width: 1.6em;
  margin-left: 4px;
  padding: 1px 6px;
  border-radius: var(--radio-chico);
  background: var(--neutro-fondo);
  font-size: 11px;
  letter-spacing: 0;
  text-align: center;
  vertical-align: 1px;
}

.cabecera__fila {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.cabecera__lado, .botones { display: inline-flex; align-items: center; gap: 10px; }
.ojo, .copiar, .campana {
  display: inline-grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--borde);
  border-radius: var(--radio-chico);
  background: var(--cristal);
  color: var(--texto);
  font-size: 16px;
  cursor: pointer;
  transition: transform var(--rapido) var(--muelle);
}
.campana[hidden] { display: none; }
.ojo:hover, .copiar:hover, .campana:hover { transform: scale(1.08); }
.ojo:active, .copiar:active, .campana:active { transform: scale(0.94); }
.temblor { animation: temblor 400ms var(--suave-curva); }
@keyframes temblor {
  20%, 60% { transform: translateX(-3px); }
  40%, 80% { transform: translateX(3px); }
}
.ojo:focus-visible, .copiar:focus-visible, .campana:focus-visible {
  outline: 2px solid var(--acento);
  outline-offset: 2px;
}
/* Hasta que el JS pone los puntos, que no se vea la cifra ni un instante. */
.oculto .dinero:not([data-v]) { visibility: hidden; }
.marca { font-weight: 700; letter-spacing: -0.01em; }

.estado {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  margin: -4px 0 -4px -8px;
  border: 0;
  border-radius: var(--radio-chico);
  background: none;
  font: inherit;
  font-size: 13px;
  text-align: left;
  color: var(--suave);
  cursor: pointer;
  transition: background var(--rapido) var(--suave-curva);
}
.estado:hover { background: var(--neutro-fondo); }
.estado:focus-visible { outline: 2px solid var(--acento); outline-offset: 2px; }
.estado.estado--cargando { opacity: 0.6; cursor: progress; }
.estado.estado--cargando .estado__punto { animation: pulso 0.6s ease-out infinite; }

.estado__punto {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--sube);
  box-shadow: 0 0 0 0 var(--sube);
  animation: pulso 2.4s ease-out infinite;
}

.estado--parado .estado__punto { background: var(--aviso); animation: none; }
.estado__texto time { cursor: help; }
.estado__hora { display: none; }
@media (hover: none) {
  .estado__hora { display: inline; }
}
.estado--parado .estado__texto { color: var(--aviso); font-weight: 600; }

@keyframes pulso {
  70% { box-shadow: 0 0 0 7px transparent; }
}

.etiqueta { margin: 26px 0 2px; color: var(--suave); }

.total {
  margin: 0;
  font-size: clamp(36px, 7vw, 56px);
  font-weight: 750;
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.total--vacio { color: var(--suave); }

.detalle {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 10px;
  margin: 12px 0 0;
}

.detalle__nota { color: var(--suave); font-size: 13px; margin-right: 8px; }

.pastilla {
  padding: 4px 11px;
  border-radius: var(--radio-chico);
  font-weight: 600;
  font-size: 14px;
}

.pastilla--sube { color: var(--sube); background: var(--sube-fondo); }
.pastilla--baja { color: var(--baja); background: var(--baja-fondo); }
.pastilla--neutro { color: var(--suave); background: var(--neutro-fondo); }

.total, .num, .pastilla, .pico__cifra, .grafica__fechas, .fila small {
  font-variant-numeric: tabular-nums;
}

/* Hueco arriba y abajo para el máximo y el mínimo: si no, pisan la línea. */
.grafica__zona { position: relative; padding: 26px 0; }
.grafica svg { display: block; width: 100%; height: 200px; overflow: visible; }
.grafica__linea {
  fill: none;
  stroke-width: 2.5;
  stroke-linejoin: round;
  stroke-linecap: round;
}
.grafica--sube .grafica__linea { stroke: var(--sube); }
.grafica--baja .grafica__linea { stroke: var(--baja); }
.grafica--neutro .grafica__linea { stroke: var(--acento); }
.grafica__area { fill: url(#relleno); }
.grafica--sube .grafica__luz { stop-color: var(--sube); stop-opacity: 0.28; }
.grafica--baja .grafica__luz { stop-color: var(--baja); stop-opacity: 0.28; }
.grafica--neutro .grafica__luz { stop-color: var(--acento); stop-opacity: 0.28; }
.grafica__sombra { stop-color: var(--fondo); stop-opacity: 0; }

.grafica__picos {
  position: absolute;
  inset: 26px 0;
  pointer-events: none;
}

.pico {
  position: absolute;
  top: 0;
  width: 9px;
  height: 9px;
  margin: -4.5px 0 0 -4.5px;
  border-radius: 50%;
  background: var(--texto);
  box-shadow: 0 0 0 3px var(--cristal);
  animation: aparece 500ms var(--muelle) both 400ms;
}
.repetir {
  padding: 4px 12px;
  border: 1px solid var(--borde);
  border-radius: var(--radio-chico);
  background: var(--cristal);
  color: var(--texto);
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: transform var(--rapido) var(--muelle);
}
.repetir:hover { color: var(--acento); transform: scale(1.04); }
.repetir:focus-visible { outline: 2px solid var(--acento); outline-offset: 2px; }

.grafica__btc {
  fill: none;
  stroke: var(--aviso);
  stroke-width: 1.5;
  stroke-dasharray: 5 5;
  opacity: 0.75;
}
.grafica__leyenda {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 18px;
  margin: 12px 0 0;
  font-size: 12.5px;
  color: var(--suave);
}
.leyenda::before {
  content: "";
  display: inline-block;
  width: 16px;
  margin-right: 6px;
  vertical-align: middle;
  border-top: 2px solid var(--acento);
}
.grafica--sube .leyenda--tuya::before { border-top-color: var(--sube); }
.grafica--baja .leyenda--tuya::before { border-top-color: var(--baja); }
.leyenda--btc::before { border-top: 2px dashed var(--aviso); }

.grafica__zona { touch-action: pan-y; }
.cursor, .cursor__punto, .cursor__texto {
  position: absolute;
  opacity: 0;
  transition: opacity var(--rapido) var(--suave-curva);
}
.cursor { top: -14px; bottom: 0; border-left: 1px dashed var(--suave); }
.cursor__punto {
  width: 9px;
  height: 9px;
  margin: -4.5px 0 0 -4.5px;
  border-radius: 50%;
  background: var(--acento);
  box-shadow: 0 0 0 3px var(--cristal);
}
.cursor__texto {
  top: -26px;
  transform: translateX(calc(var(--x) * -1));
  padding: 2px 8px;
  border-radius: 8px;
  background: var(--cristal);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.viendo .cursor, .viendo .cursor__punto, .viendo .cursor__texto { opacity: 1; }
/* Mientras miras un punto, las cifras del máximo y el mínimo estorban. */
.viendo .pico { opacity: 0.25; }
.viendo .pico__cifra { opacity: 0; }
/* Repitiendo, el máximo y el mínimo destriparían cómo acaba. */
.repitiendo .pico { opacity: 0; }

.pico__cifra {
  position: absolute;
  left: 50%;
  bottom: 14px;
  transform: translateX(calc(var(--x) * -1));
  padding: 2px 8px;
  border-radius: 8px;
  background: var(--cristal);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
.pico--abajo .pico__cifra { bottom: auto; top: 14px; }

.grafica__fechas {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 12px;
  color: var(--suave);
}

.lista { list-style: none; margin: 0; padding: 0; }

.fila {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) 100px minmax(0, 1fr) minmax(0, 1fr) 110px;
  align-items: center;
  gap: 16px;
  padding: 12px 0;
  border-top: 1px solid var(--linea-fila);
  animation: aparece 500ms var(--muelle) both;
}

.recargado .fila { animation: none; }

.fila:first-child { border-top: 0; }

.fila--total { border-top: 2px solid var(--linea-fila); }
.fila--total strong { font-weight: 750; }
/* Ancho fijo para el precio: con auto cada fila medía distinto y las rayas no
   quedaban en línea. 8.5em da para $1.000.000,00. */
.fila--cerca {
  margin: 0 -12px;
  padding-left: 12px;
  padding-right: 12px;
  border-radius: 14px;
  background: var(--neutro-fondo);
  box-shadow: inset 3px 0 var(--acento);
}
.fila--cerca + .fila { border-top-color: transparent; }
.cerca { color: var(--acento); font-weight: 600; white-space: nowrap; }
.fila--corta { grid-template-columns: minmax(0, 1fr) 80px 8.5em; }
.fila--alerta { grid-template-columns: minmax(0, 1fr) auto; }

@keyframes aparece {
  from { opacity: 0; transform: scale(0.96); }
}

.fila__nombre { display: flex; flex-direction: column; min-width: 0; }
.moneda { color: inherit; text-decoration: none; }
.moneda:hover { color: var(--acento); text-decoration: underline; }
.moneda:focus-visible { outline: 2px solid var(--acento); outline-offset: 2px; }
.fila__nombre strong { font-weight: 650; }
.fila__nombre small, .num small {
  display: block;
  color: var(--suave);
  font-size: 12.5px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.flecha { color: var(--acento); }

.num { text-align: right; font-weight: 600; white-space: nowrap; }
.num--sube, .num small.num--sube { color: var(--sube); }
.num--baja, .num small.num--baja { color: var(--baja); }
.num--neutro { color: var(--suave); }
.num--listo { color: var(--acento); }

.mini { width: 100%; height: 28px; }
.mini path { fill: none; stroke-width: 1.75; stroke-linejoin: round; }
.mini--sube path { stroke: var(--sube); }
.mini--baja path { stroke: var(--baja); }
.mini--neutro path { stroke: var(--acento); }
.mini--vacia path { stroke: var(--suave); stroke-dasharray: 3 4; opacity: 0.5; }

.peso { display: flex; flex-direction: column; gap: 4px; }
.peso small { color: var(--suave); font-size: 12px; text-align: right; }

.peso__barra {
  height: 6px;
  border-radius: var(--radio-chico);
  background: var(--neutro-fondo);
  overflow: hidden;
}

.peso__barra span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--acento), var(--mancha-2));
}

.vacio, .nota { margin: 0; color: var(--suave); }
.nota { margin-top: 10px; font-size: 13px; }

code {
  font-size: 0.92em;
  padding: 1px 6px;
  border-radius: 6px;
  background: var(--neutro-fondo);
}

/* Cuando cambia una cifra al refrescar. */
.latido { animation: latido 900ms var(--muelle); }

@keyframes latido {
  30% { transform: scale(1.06); color: var(--acento); }
}

.pie {
  max-width: 1080px;
  margin: 0 auto;
  padding: 18px 16px 32px;
  text-align: center;
  font-size: 12.5px;
  color: var(--suave);
}

.pie a { color: inherit; text-underline-offset: 3px; }
.pie a:hover { color: var(--acento); }

.cal__intro { margin: -6px 0 14px; }
.cal__scroll { overflow-x: auto; padding-bottom: 4px; }
.cal__scroll, .cal__pie { --casilla: 13px; }
.cal {
  display: grid;
  grid-template-columns: auto max-content;
  grid-template-rows: auto auto;
  gap: 4px 6px;
  width: max-content;
}
.cal__meses {
  grid-column: 2;
  display: grid;
  grid-template-columns: repeat(var(--semanas), var(--casilla));
  column-gap: 3px;
  font-size: 11px;
  color: var(--suave);
}
.cal__meses span { white-space: nowrap; }
.cal__semana {
  grid-row: 2;
  display: grid;
  grid-template-rows: repeat(7, var(--casilla));
  row-gap: 3px;
  font-size: 10px;
  line-height: var(--casilla);
  color: var(--suave);
}
.cal__rejilla {
  grid-row: 2;
  grid-column: 2;
  display: grid;
  grid-template-rows: repeat(7, var(--casilla));
  grid-auto-flow: column;
  grid-auto-columns: var(--casilla);
  gap: 3px;
}
.cal__dia {
  display: inline-block;
  width: var(--casilla);
  height: var(--casilla);
  border-radius: 3px;
  background: var(--neutro-fondo);
}
.cal__dia--futuro { background: none; }
.cal__dia--vacia { background: var(--linea-fila); }
.cal__dia--igual { background: color-mix(in srgb, var(--suave) 35%, transparent); }
.cal__dia--sube-1 { background: color-mix(in srgb, var(--sube) 25%, transparent); }
.cal__dia--sube-2 { background: color-mix(in srgb, var(--sube) 50%, transparent); }
.cal__dia--sube-3 { background: color-mix(in srgb, var(--sube) 75%, transparent); }
.cal__dia--sube-4 { background: var(--sube); }
.cal__dia--baja-1 { background: color-mix(in srgb, var(--baja) 25%, transparent); }
.cal__dia--baja-2 { background: color-mix(in srgb, var(--baja) 50%, transparent); }
.cal__dia--baja-3 { background: color-mix(in srgb, var(--baja) 75%, transparent); }
.cal__dia--baja-4 { background: var(--baja); }
.cal__dia--hoy { outline: 2px solid var(--texto); outline-offset: 1px; }
.cal__pie {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 8px 18px;
  margin-top: 12px;
  font-size: 12.5px;
  color: var(--suave);
}
.cal__pie p { margin: 0; }
.cal__escala { --casilla: 11px; display: inline-flex; align-items: center; gap: 3px; }
.cal__escala span:first-child { margin-right: 4px; }
.cal__escala span:last-child { margin-left: 4px; }

.sim__intro { margin: -6px 0 14px; }
.sim__fila {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) 70px 9em;
  align-items: center;
  gap: 16px;
  padding: 8px 0;
}
.sim__fila:first-child {
  padding-bottom: 14px;
  margin-bottom: 6px;
  border-bottom: 1px solid var(--linea-fila);
}
.sim__fila label { display: flex; flex-direction: column; min-width: 0; }
.sim__fila small { color: var(--suave); font-size: 12.5px; }
.sim__fila input { width: 100%; accent-color: var(--acento); cursor: pointer; }
.sim__pct.num--sube, .sim__precio.num--sube { color: var(--sube); }
.sim__pct.num--baja, .sim__precio.num--baja { color: var(--baja); }
.sim__resultado {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-top: 16px;
}
.sim__resultado > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 14px 16px;
  border-radius: 16px;
  background: var(--neutro-fondo);
}
.sim__resultado small { color: var(--suave); font-size: 12.5px; }
.sim__resultado strong { font-size: 22px; text-align: left; }
.sim__resultado .num--sube { color: var(--sube); }
.sim__resultado .num--baja { color: var(--baja); }
.sim__volver {
  margin-top: 14px;
  padding: 8px 14px;
  border: 1px solid var(--borde);
  border-radius: var(--radio-chico);
  background: var(--cristal);
  color: var(--texto);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.sim__volver:hover { color: var(--acento); }
.sim__volver:focus-visible { outline: 2px solid var(--acento); outline-offset: 2px; }

@media screen and (max-width: 760px) {
  /* Con tres botones al lado el estado se quedaba en tres líneas: los botones
     suben a la fila del nombre y el estado baja a todo lo ancho. */
  .cabecera__lado { display: contents; }
  .estado { order: 1; flex-basis: 100%; }
  .sim__fila { grid-template-columns: minmax(0, 1fr) auto; gap: 4px 12px; }
  .sim__fila input { grid-column: 1 / -1; grid-row: 2; }
  .sim__precio { display: none; }
  .panel { grid-template-columns: minmax(0, 1fr); gap: 14px; padding-top: 18px; }
  .tarjeta, .cabecera { padding: 18px; }
  .fila { grid-template-columns: minmax(0, 1fr) auto; gap: 4px 12px; }
  .fila .mini { display: none; }
  .fila .peso { grid-column: 1 / -1; flex-direction: row; align-items: center; }
  .fila .peso__barra { flex: 1; }
  /* Por clase: contando spans fallaba cuando la mini es el "sin histórico". */
  .lista--cartera .fila > .ganancia { grid-column: 2; }
  .grafica svg { height: 150px; }
}

/* Al imprimir, papel blanco aunque tengas el modo oscuro: sin manchas ni cristal. */
@media print {
  :root {
    --fondo: #fff;
    --texto: #16131f;
    --suave: #5d5873;
    --cristal: #fff;
    --borde: #dcd8e6;
    --linea-fila: #e8e5ef;
    --acento: #5536d6;
    --sube: #0a7d55;
    --sube-fondo: rgba(10, 125, 85, 0.1);
    --baja: #c0303f;
    --baja-fondo: rgba(192, 48, 63, 0.1);
    --neutro-fondo: rgba(93, 88, 115, 0.1);
    --aviso: #a36800;
  }
  @page { margin: 14mm; }
  body {
    background: none;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  body::after, .tarjeta::before, .cabecera::before,
  .ojo, .copiar, .campana, .simulador, .repetir {
    display: none;
  }
  .tarjeta, .cabecera {
    box-shadow: none;
    -webkit-backdrop-filter: none;
    backdrop-filter: none;
    break-inside: avoid;
  }
  *, *::before, *::after {
    animation: none !important;
    transition: none !important;
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important;
    transition: none !important;
  }
}
"""

CSS = CSS.replace("__GRANO__", GRANO)

CLAVE = "panel-oculto"

# Va en el <head> para que al recargar no asomen las cifras antes de taparlas.
ANTES = (
    f"if (localStorage.getItem('{CLAVE}') === '1') "
    "document.documentElement.classList.add('oculto');"
    # La clave va también al manifiesto, para que la app instalada abra con ella.
    "if (location.search) document.querySelector('link[rel=manifest]').href = "
    "'manifest.webmanifest' + location.search;"
)

JS = f"""
(function () {{
  var cada = {REFRESCO} * 1000;
  var titulo = document.title;
  function oculto() {{ return localStorage.getItem('{CLAVE}') === '1'; }}
  // Dónde está cada deslizador (-1 a 1). Fuera de <main> a propósito: el refresco
  // de cada minuto cambia la página entera y no quiero que te los devuelva a cero.
  var sim = {{}};
  function simular() {{
    var sec = document.querySelector('[data-sim]');
    if (!sec) return;
    var d = JSON.parse(sec.dataset.sim);
    var tapado = oculto();
    function dinero(v) {{
      if (tapado) return '•••';
      var p = Math.abs(v).toFixed(2).split('.');
      var entero = p[0].replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, '.');
      return (v < 0 ? '-' : '') + d.simbolo + entero + ',' + p[1];
    }}
    function pct(x) {{
      var t = Math.abs(x) < 0.5 ? '0' : (x > 0 ? '+' : '') + x.toFixed(0);
      return t.replace('.', ',') + ' %';
    }}
    function tono(el, x) {{
      el.classList.toggle('num--sube', x >= 0.5);
      el.classList.toggle('num--baja', x <= -0.5);
    }}
    function poner(id, pos) {{
      var input = sec.querySelector('input[data-id="' + id + '"]');
      if (!input) return;
      input.value = pos;
      var cambio = (Math.pow(d.tope, pos) - 1) * 100;
      var etiqueta = input.parentNode.querySelector('.sim__pct');
      etiqueta.textContent = pct(cambio);
      tono(etiqueta, cambio);
    }}
    var hoy = 0, total = 0, movido = false;
    d.monedas.forEach(function (m) {{
      var pos = sim[m.id] || 0;
      if (pos) movido = true;
      var precio = m.precio * Math.pow(d.tope, pos);
      hoy += m.cantidad * m.precio;
      total += m.cantidad * precio;
      poner(m.id, pos);
      var el = sec.querySelector('[data-precio="' + m.id + '"]');
      el.textContent = dinero(precio);
      tono(el, (precio / m.precio - 1) * 100);
    }});
    poner('*', sim['*'] || 0);
    var dif = (total / hoy - 1) * 100;
    sec.querySelector('.sim__total').textContent = dinero(total);
    var difEl = sec.querySelector('.sim__dif');
    difEl.textContent = movido
      ? (tapado ? '' : dinero(total - hoy) + ' · ') + pct(dif) + ' sobre hoy'
      : 'lo mismo que hoy';
    tono(difEl, dif);
    var ganancia = sec.querySelector('.sim__ganancia');
    if (ganancia) {{
      var g = total - d.invertido;
      ganancia.textContent = dinero(g);
      tono(ganancia, g);
      sec.querySelector('.sim__gpct').textContent = pct(g / d.invertido * 100);
    }}
    var hacienda = sec.querySelector('.sim__hacienda');
    if (hacienda) {{
      // Lo mismo que impuestos.por_tramos(). Vendiéndolo todo, lo que costó es
      // justo lo invertido: no hace falta el FIFO.
      var base = Math.max(0, total - d.invertido), cuota = 0, desde = 0;
      d.tramos.forEach(function (t) {{
        var hasta = t[0] === null ? Infinity : t[0];
        if (base <= desde) return;
        cuota += (Math.min(base, hasta) - desde) * t[1] / 100;
        desde = hasta;
      }});
      hacienda.textContent = dinero(cuota);
      sec.querySelector('.sim__tipo').textContent = base > 0
        ? 'un ' + (cuota / base * 100).toFixed(1).replace('.', ',') +
          ' % de lo ganado'
        : 'sin ganancia, nada';
    }}
    sec.querySelector('.sim__volver').hidden = !movido;
  }}
  document.addEventListener('input', function (e) {{
    var id = e.target.dataset && e.target.dataset.id;
    if (!id || !e.target.closest('[data-sim]')) return;
    var pos = parseFloat(e.target.value);
    if (id === '*') {{
      // Mover "todas" las pone todas ahí; mover una suelta deja "todas" donde estaba.
      sim = {{ '*': pos }};
      JSON.parse(e.target.closest('[data-sim]').dataset.sim).monedas
        .forEach(function (m) {{ sim[m.id] = pos; }});
    }} else {{
      sim[id] = pos;
    }}
    simular();
  }});
  function tapar() {{
    var si = oculto();
    document.documentElement.classList.toggle('oculto', si);
    document.querySelectorAll('.dinero').forEach(function (el) {{
      if (!('v' in el.dataset)) el.dataset.v = el.textContent;
      el.textContent = si ? '•••' : el.dataset.v;
    }});
    document.title = si ? '••• · CryptoPriceTracker' : titulo;
    var ojo = document.querySelector('.ojo');
    if (ojo) {{
      ojo.setAttribute('aria-pressed', si);
      ojo.title = (si ? 'Enseñar' : 'Ocultar') + ' cifras (O)';
      ojo.textContent = si ? '🙈' : '👁';
    }}
    simular();
  }}
  function copiarResumen(boton) {{
    var texto = oculto() ? boton.dataset.oculto : boton.dataset.texto;
    navigator.clipboard.writeText(texto).then(function () {{
      boton.textContent = '✓';
      boton.title = 'Copiado';
      setTimeout(function () {{
        boton.textContent = '📋';
        boton.title = 'Copiar resumen';
      }}, 1500);
    }}, function () {{ temblar(boton); }});
  }}
  function temblar(boton) {{
    boton.classList.remove('temblor');
    void boton.offsetWidth;
    boton.classList.add('temblor');
  }}
  var hayAvisos = 'Notification' in window;
  function avisando() {{
    return hayAvisos && Notification.permission === 'granted' &&
      localStorage.getItem('panel-avisos') === '1';
  }}
  function pintarCampana() {{
    var c = document.querySelector('.campana');
    if (!c || !hayAvisos) return;
    var si = avisando();
    c.hidden = false;
    c.textContent = si ? '🔔' : '🔕';
    c.setAttribute('aria-pressed', si);
    c.title = si ? 'Te aviso también aquí (pulsa para dejarlo)'
      : 'Avisarme también en este navegador';
  }}
  function campana(boton) {{
    if (avisando()) {{
      localStorage.setItem('panel-avisos', '0');
      pintarCampana();
      return;
    }}
    Notification.requestPermission().then(function (permiso) {{
      if (permiso === 'granted') {{
        localStorage.setItem('panel-avisos', '1');
        new Notification('CryptoPriceTracker', {{
          body: 'Listo: cuando salte un aviso, te llega también aquí.',
        }});
      }} else {{
        // Bloqueado en el navegador: desde aquí ya no se puede volver a pedir.
        boton.title = 'El navegador tiene bloqueados los avisos de esta página';
        temblar(boton);
      }}
      pintarCampana();
    }});
  }}
  function avisosDe(raiz) {{
    var el = raiz.querySelector('[data-avisos]');
    return el ? JSON.parse(el.dataset.avisos) : [];
  }}
  // Los que ya estaban al abrir no se avisan: solo los que llegan con él abierto.
  var vistos = {{}};
  avisosDe(document).forEach(function (a) {{ vistos[a.id] = true; }});
  function avisarNuevos() {{
    avisosDe(document).forEach(function (a) {{
      if (vistos[a.id]) return;
      vistos[a.id] = true;
      if (avisando()) new Notification(a.titulo, {{ body: a.texto, tag: a.id }});
    }});
  }}
  pintarCampana();
  function alternar() {{
    localStorage.setItem('{CLAVE}', oculto() ? '0' : '1');
    tapar();
  }}
  document.addEventListener('click', function (e) {{
    if (e.target.closest('.sim__volver')) {{
      sim = {{}};
      simular();
      return;
    }}
    var copiar = e.target.closest('.copiar');
    var boton = e.target.closest('.campana');
    if (boton) campana(boton);
    else if (copiar) copiarResumen(copiar);
    else if (e.target.closest('.ojo')) alternar();
    else if (e.target.closest('.estado')) refrescar();
  }});
  document.addEventListener('keydown', function (e) {{
    // Con Cmd o Ctrl es del navegador: Cmd+R tiene que seguir recargando.
    if (e.metaKey || e.ctrlKey || e.altKey || e.repeat) return;
    var tecla = e.key.toLowerCase();
    if (tecla === 'r') refrescar();
    else if (tecla === 'o') alternar();
  }});
  tapar();
  // La gráfica se cambia entera en cada refresco: hay que volver a engancharla.
  function enganchar() {{
    var zona = document.querySelector('.grafica__zona[data-puntos]');
    if (!zona) return;
    var puntos = JSON.parse(zona.dataset.puntos);
    var linea = zona.querySelector('.cursor');
    var punto = zona.querySelector('.cursor__punto');
    var texto = zona.querySelector('.cursor__texto');
    var corte = zona.querySelector('.grafica__corte');
    var boton = zona.parentNode.querySelector('.repetir');
    var paso = null;
    function ponerEn(i) {{
      var p = puntos[i];
      var x = (i / (puntos.length - 1) * 100) + '%';
      linea.style.left = punto.style.left = texto.style.left = x;
      texto.style.setProperty('--x', x);
      punto.style.top = p[2] + '%';
      var btc = p[3] ? ' · en bitcoin ' + (oculto() ? '•••' : p[3]) : '';
      texto.textContent = (oculto() ? '•••' : p[1]) + btc + ' · ' + p[0];
      zona.classList.add('viendo');
    }}
    function parar() {{
      clearTimeout(paso);
      paso = null;
      zona.classList.remove('repitiendo');
      corte.setAttribute('width', {ANCHO});
      boton.textContent = '▶ Ver cómo fue';
    }}
    // La semana en unos seis segundos, dibujándose de izquierda a derecha.
    function repetir() {{
      if (paso !== null) {{
        parar();
        zona.classList.remove('viendo');
        return;
      }}
      var i = 0;
      boton.textContent = '■ Parar';
      zona.classList.add('repitiendo');
      (function siguiente() {{
        // Si el refresco del minuto ha cambiado la gráfica, esta ya no está.
        if (!zona.isConnected) return;
        corte.setAttribute('width', i / (puntos.length - 1) * {ANCHO});
        ponerEn(i);
        if (i++ < puntos.length - 1) {{
          paso = setTimeout(siguiente, 6000 / puntos.length);
        }} else {{
          paso = null;
          zona.classList.remove('repitiendo');
          boton.textContent = '↻ Otra vez';
        }}
      }})();
    }}
    function mirar(e) {{
      if (paso !== null) parar();
      var caja = zona.getBoundingClientRect();
      var f = Math.min(1, Math.max(0, (e.clientX - caja.left) / caja.width));
      ponerEn(Math.round(f * (puntos.length - 1)));
    }}
    boton.addEventListener('click', repetir);
    zona.addEventListener('pointermove', mirar);
    zona.addEventListener('pointerdown', mirar);
    zona.addEventListener('pointerleave', function () {{
      if (paso === null) zona.classList.remove('viendo');
    }});
  }}
  enganchar();
  // El calendario puede no caber en el móvil: que se vea lo último, no enero.
  function alFinal() {{
    document.querySelectorAll('.cal__scroll').forEach(function (el) {{
      el.scrollLeft = el.scrollWidth;
    }});
  }}
  alFinal();
  // Solo al abrir: en cada refresco contaría desde cero y marearía.
  function contar() {{
    var el = document.querySelector('.total .dinero');
    var quieto = matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!el || oculto() || quieto) return;
    var texto = el.dataset.v;
    var m = texto.match(/\\d[\\d.]*,\\d{{2}}/);
    if (!m) return;
    var fin = parseFloat(m[0].replace(/\\./g, '').replace(',', '.'));
    var antes = texto.slice(0, m.index);
    var despues = texto.slice(m.index + m[0].length);
    var inicio = Date.now();
    function cifra(v) {{
      var p = v.toFixed(2).split('.');
      return p[0].replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, '.') + ',' + p[1];
    }}
    // Con setTimeout y no requestAnimationFrame: sin fotogramas (pestaña de fondo,
    // Chrome sin ventana) este se quedaba a medias y la página no terminaba de entrar.
    function paso() {{
      // Si lo tapas a mitad, que no siga escribiendo la cifra encima.
      if (oculto()) return;
      var x = Math.min(1, (Date.now() - inicio) / 700);
      var suave = 1 - Math.pow(1 - x, 3);
      el.textContent = x < 1 ? antes + cifra(fin * suave) + despues : texto;
      if (x < 1) setTimeout(paso, 16);
    }}
    paso();
  }}
  contar();
  function cifras(raiz) {{
    var mapa = {{}};
    raiz.querySelectorAll('[data-k]').forEach(function (el) {{
      mapa[el.dataset.k] = el.textContent.trim();
    }});
    return mapa;
  }}
  var ultimo = Date.now();
  function refrescar() {{
    var estado = document.querySelector('.estado');
    // Un segundo toque mientras carga no lanza otra petición.
    if (estado && estado.classList.contains('estado--cargando')) return;
    if (estado) estado.classList.add('estado--cargando');
    ultimo = Date.now();
    fetch(location.href, {{ cache: 'no-store' }})
      .then(function (r) {{ return r.ok ? r.text() : Promise.reject(r.status); }})
      .then(function (html) {{
        var nuevo = new DOMParser().parseFromString(html, 'text/html');
        var antes = cifras(document);
        document.documentElement.classList.add('recargado');
        document.querySelector('main').replaceWith(nuevo.querySelector('main'));
        // El fondo va en body, que no se cambia: el tono del día, a mano.
        document.body.className = nuevo.body.className;
        document.body.style.cssText = nuevo.body.style.cssText;
        titulo = nuevo.title;
        enganchar();
        alFinal();
        simular();
        pintarCampana();
        avisarNuevos();
        document.querySelector('link[rel=icon]').href =
          nuevo.querySelector('link[rel=icon]').href;
        tapar();
        document.querySelectorAll('[data-k]').forEach(function (el) {{
          var k = el.dataset.k;
          if (k in antes && antes[k] !== el.textContent.trim()) {{
            el.classList.add('latido');
          }}
        }});
      }})
      // Si el panel se ha caído, se queda lo último que había.
      .catch(function () {{
        if (estado) estado.classList.remove('estado--cargando');
      }});
  }}
  // Con la pestaña de fondo no pido nada (salvo con los avisos puestos); al volver,
  // si toca, refresco al momento.
  // Con los avisos puestos sí, aunque esté de fondo: es justo cuando sirven.
  setInterval(function () {{
    if (!document.hidden || avisando()) refrescar();
  }}, cada);
  document.addEventListener('visibilitychange', function () {{
    if (!document.hidden && Date.now() - ultimo >= cada) refrescar();
  }});
}})();
"""

# Para instalarlo como app en el móvil.
MANIFIESTO = {
    "name": "CryptoPriceTracker",
    "short_name": "Cartera",
    "lang": "es",
    "display": "standalone",
    "background_color": "#0d0b16",
    "theme_color": "#0d0b16",
    "icons": [
        {
            "src": f"icono-{lado}.png",
            "sizes": f"{lado}x{lado}",
            "type": "image/png",
            "purpose": "any maskable",
        }
        for lado in (192, 512)
    ],
}


def manifiesto(ruta: str) -> dict:
    """El de arriba, abriendo donde lo instalaste: con la clave, si la llevaba.
    Del resto de la dirección no copia nada."""
    clave = parse_qs(urlsplit(ruta).query).get("clave", [""])[0]
    inicio = "./?" + urlencode({"clave": clave}) if clave else "./"
    return {**MANIFIESTO, "start_url": inicio}


# Lo que abre el botón de /panel: Telegram firma quién eres y con eso entra.
APP = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Tu cartera</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
body {
  margin: 0; min-height: 100vh; display: grid; place-items: center;
  font: 16px system-ui, sans-serif; background: #f4f1fb; color: #1c1830;
}
@media (prefers-color-scheme: dark) {
  body { background: #0d0b16; color: #ece9f6; }
}
</style>
</head>
<body>
<p id="aviso">Abriendo tu panel…</p>
<script>
(function () {
  function decir(texto) { document.getElementById('aviso').textContent = texto; }
  var tg = window.Telegram && Telegram.WebApp;
  if (!tg || !tg.initData) {
    decir('Ábrelo con el botón de /panel en Telegram.');
    return;
  }
  tg.ready();
  tg.expand();
  // Rutas relativas: así vale aunque el panel cuelgue de una subcarpeta.
  fetch('app/entrar', { method: 'POST', body: tg.initData })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (d) {
      location.replace('app/panel?sesion=' + encodeURIComponent(d.sesion));
    })
    .catch(function (e) {
      decir(e === 403 ? 'Este panel no es tuyo.'
                      : 'No llego al panel. ¿Está en marcha?');
    });
})();
</script>
</body>
</html>
"""


# --- La página de /enlace: para enseñar, solo con porcentajes ---


def _fila_compartida(f: Fila) -> str:
    return f"""
<li class="fila">
  <div class="fila__nombre"><strong>{_enlace(f.coin_id)}</strong></div>
  {_mini(f.linea, _tono(f.cambio_24h))}
  <span class="num num--{_tono(f.cambio_24h)}">{_pct(f.cambio_24h)}
    <small>24 h</small></span>
  <span class="num num--{_tono(f.porcentaje)} ganancia">{_pct(f.porcentaje)}
    <small>desde la compra</small></span>
  <div class="peso">
    <div class="peso__barra"><span style="width:{f.peso:.1f}%"></span></div>
    <small>{_pct(f.peso, signo=False)} del total</small>
  </div>
</li>"""


def _grafica_compartida(p: Panel) -> str:
    if len(p.serie) < 2:
        return ""
    puntos = muestrear(p.serie, PUNTOS_GRAFICA)
    valores = [v for _, v in puntos]
    # Sin cifras en el eje ni puntos con valor: la forma no dice cuánto tienes.
    linea = trazo(valores, ANCHO, ALTO)
    area = f"{linea} L{ANCHO},{ALTO} L0,{ALTO} Z"
    desde, hasta = puntos[0][0].astimezone(), puntos[-1][0].astimezone()
    semana = cambio(valores[-1], valores[0])
    cuerpo = f"""
<div class="grafica grafica--{_tono(semana)}">
  <div class="grafica__zona">
  <svg viewBox="0 0 {ANCHO} {ALTO}" preserveAspectRatio="none" role="img"
       aria-label="Cómo ha ido la cartera en los últimos días">
    <defs>
      <linearGradient id="relleno" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" class="grafica__luz"/>
        <stop offset="1" class="grafica__sombra"/>
      </linearGradient>
    </defs>
    <path class="grafica__area" d="{area}"/>
    <path class="grafica__linea" d="{linea}" vector-effect="non-scaling-stroke"/>
  </svg>
  </div>
  <div class="grafica__fechas">
    <span>{desde:%d/%m %H:%M}</span><span>{hasta:%d/%m %H:%M}</span>
  </div>
</div>"""
    titulo = (
        "Los últimos 7 días · "
        f'<span class="h2__cambio num--{_tono(semana)}">{_pct(semana)}</span>'
    )
    return _tarjeta(titulo, cuerpo, 1, "grafica")


def pagina_compartida(p: Panel, caduca: datetime) -> str:
    """Lo que ve quien abre tu enlace: cómo te va, pero ni una cifra de dinero."""
    grande, nota, dia = p.porcentaje, "desde que compró", ""
    if grande is None:
        grande, nota = p.cambio_24h, "en 24 h"
    elif p.cambio_24h is not None:
        dia = (
            f'<span class="pastilla pastilla--{_tono(p.cambio_24h)}">'
            f'{_pct(p.cambio_24h)}</span><span class="detalle__nota">en 24 h</span>'
        )
    cabecera = f"""
<header class="cabecera seccion" style="--i:0">
  <div class="cabecera__fila"><span class="marca">CryptoPriceTracker</span></div>
  <p class="etiqueta">Una cartera, en porcentajes</p>
  <p class="total num--{_tono(grande)}">{_pct(grande)}</p>
  <p class="detalle"><span class="detalle__nota">{nota}</span>{dia}</p>
  {_animo(p)}
</header>"""
    filas = "".join(_fila_compartida(f) for f in p.filas)
    reparto = (
        _tarjeta(
            f"Lo que lleva{_cuenta(len(p.filas))}",
            f'<ul class="lista lista--cartera">{filas}</ul>',
            2,
            "ancha",
        )
        if p.filas
        else ""
    )
    hasta = caduca.astimezone()
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="robots" content="noindex">
<meta name="referrer" content="no-referrer">
<title>Una cartera · CryptoPriceTracker</title>
<style>{CSS}</style>
</head>
<body{_fondo(p)}>
<main class="panel">{cabecera}{_grafica_compartida(p)}{reparto}</main>
<footer class="pie">
  Solo porcentajes: ni cantidades ni dinero. Este enlace caduca el
  {hasta:%d/%m} a las {hasta:%H:%M}.
</footer>
</body>
</html>"""
