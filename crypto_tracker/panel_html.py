"""La página del panel. Los datos vienen hechos de panel.py."""

from datetime import datetime
from html import escape
from urllib.parse import quote

from . import version
from .mensajes.base import SIMBOLOS, _num, describir
from .panel import PUNTOS_GRAFICA, Alerta, Fila, Panel, Vigilada, hace, muestrear, trazo
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
        return '<span class="mini mini--vacia">sin histórico</span>'
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


def _cabecera(p: Panel, ahora: datetime, parado: bool) -> str:
    estado = "parado" if parado else "vivo"
    cuando = _cuando(p, ahora)
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
<header class="cabecera seccion" style="--i:0">
  <div class="cabecera__fila">
    <span class="marca">CryptoPriceTracker</span>
    <span class="cabecera__lado">
      <button class="estado estado--{estado}" type="button"
              title="Actualizar ahora">
        <span class="estado__punto"></span>{aviso}
      </button>
      <button class="ojo" type="button" aria-pressed="false"
              title="Ocultar cifras">👁</button>
    </span>
  </div>
  <p class="etiqueta">Tu cartera</p>
  {grande}
  {detalle}
</header>"""


def _pico(valores: list[float], i: int, arriba: bool, moneda: str) -> str:
    x = i / (len(valores) - 1) * 100
    clase = "pico" if arriba else "pico pico--abajo"
    # El desplazamiento va con x: en el borde izquierdo la cifra queda a la
    # derecha del punto y en el derecho a la izquierda, sin salirse nunca.
    return (
        f'<span class="{clase}" style="left:{x:.1f}%;--x:{x:.1f}%">'
        f'<span class="pico__cifra">{_dinero(valores[i], moneda)}</span></span>'
    )


def _picos(valores: list[float], moneda: str) -> str:
    alto, bajo = max(valores), min(valores)
    if alto == bajo:
        punto = _pico(valores, 0, True, moneda)
        return f'<div class="grafica__picos grafica__picos--plana">{punto}</div>'
    puntos = _pico(valores, valores.index(alto), True, moneda) + _pico(
        valores, valores.index(bajo), False, moneda
    )
    return f'<div class="grafica__picos">{puntos}</div>'


def _grafica(p: Panel) -> str:
    if len(p.serie) < 2:
        cuerpo = (
            '<p class="vacio">Aún no hay precios suficientes para dibujarla. '
            "Vuelve cuando el bot lleve un rato guardando.</p>"
        )
        return _tarjeta("Los últimos 7 días", cuerpo, 1, "grafica")

    puntos = muestrear(p.serie, PUNTOS_GRAFICA)
    valores = [v for _, v in puntos]
    linea = trazo(valores, ANCHO, ALTO)
    area = f"{linea} L{ANCHO},{ALTO} L0,{ALTO} Z"
    tono = _tono(valores[-1] - valores[0])
    desde, hasta = puntos[0][0].astimezone(), puntos[-1][0].astimezone()

    cuerpo = f"""
<div class="grafica grafica--{tono}">
  <div class="grafica__zona">
  {_picos(valores, p.moneda)}
  <svg viewBox="0 0 {ANCHO} {ALTO}" preserveAspectRatio="none" role="img"
       aria-label="Lo que ha valido tu cartera en los últimos días">
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
    return _tarjeta("Los últimos 7 días", cuerpo, 1, "grafica")


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
    <strong>{_nombre(f.coin_id)}</strong>
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
    return _tarjeta("Lo que tienes", cuerpo, 2, "ancha")


def _vigilada(v: Vigilada, moneda: str) -> str:
    tono = _tono(v.cambio_24h)
    return f"""
<li class="fila fila--corta">
  <div class="fila__nombre">
    <strong>{_nombre(v.coin_id)}</strong>
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
    return _tarjeta("Lo que vigilo", cuerpo, 3)


def _alerta(a: Alerta, moneda: str) -> str:
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
    return f"""
<li class="fila fila--alerta">
  <div class="fila__nombre">
    <strong>{nombre} <span class="flecha">{flecha}</span>
      {_importe(a.objetivo, moneda)}</strong>
    <small>#{a.id} · ahora {_importe(a.precio, moneda)}</small>{nota}
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
        filas = "".join(_alerta(a, p.moneda) for a in p.alertas)
        cuerpo = f'<ul class="lista">{filas}</ul>'
    return _tarjeta("Alertas pendientes", cuerpo, 4)


def _titulo(p: Panel) -> str:
    if p.total is None:
        return "Tu cartera · CryptoPriceTracker"
    titulo = _importe(p.total, p.moneda)
    if p.cambio_24h is not None:
        titulo += f" · {_pct(p.cambio_24h)}"
    return escape(titulo)


# Los mismos que --sube, --baja y --acento del modo claro. Aquí no llegan las
# variables CSS: el icono es una imagen aparte.
ICONO_COLOR = {"sube": "#0f9f6e", "baja": "#e0445a", "neutro": "#6d4aff"}
ICONO_TRAZO = {
    "sube": "M7 22 L13 15 L18 19 L25 10",
    "baja": "M7 10 L13 17 L18 13 L25 22",
    "neutro": "M7 16 H25",
}


def _icono(p: Panel) -> str:
    tono = _tono(p.cambio_24h)
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
        f"<rect width='32' height='32' rx='8' fill='{ICONO_COLOR[tono]}'/>"
        f"<path d='{ICONO_TRAZO[tono]}' fill='none' stroke='white' "
        "stroke-width='3.5' stroke-linecap='round' stroke-linejoin='round'/></svg>"
    )
    return "data:image/svg+xml," + quote(svg)


def _tarjeta(titulo: str, cuerpo: str, orden: int, clase: str = "") -> str:
    extra = f" tarjeta--{clase}" if clase else ""
    return f"""
<section class="tarjeta seccion{extra}" style="--i:{orden}">
  <h2>{titulo}</h2>
  {cuerpo}
</section>"""


def pagina(p: Panel, ahora: datetime, parado: bool) -> str:
    contenido = "".join(
        [
            _cabecera(p, ahora, parado),
            _grafica(p),
            _cartera(p),
            _vigiladas(p),
            _alertas(p),
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
<link rel="icon" href="{_icono(p)}">
<script>{ANTES}</script>
<style>{CSS}</style>
</head>
<body>
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

.cabecera__fila {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.cabecera__lado { display: inline-flex; align-items: center; gap: 10px; }
.ojo {
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
.ojo:hover { transform: scale(1.08); }
.ojo:active { transform: scale(0.94); }
.ojo:focus-visible { outline: 2px solid var(--acento); outline-offset: 2px; }
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
.pico--abajo { top: 100%; }
.grafica__picos--plana .pico { top: 50%; }

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
.fila--corta { grid-template-columns: minmax(0, 1fr) 80px auto; }
.fila--alerta { grid-template-columns: minmax(0, 1fr) auto; }

@keyframes aparece {
  from { opacity: 0; transform: scale(0.96); }
}

.fila__nombre { display: flex; flex-direction: column; min-width: 0; }
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
.mini--vacia { font-size: 12px; color: var(--suave); text-align: center; }

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

@media screen and (max-width: 760px) {
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
  body::after, .tarjeta::before, .cabecera::before, .ojo { display: none; }
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
)

JS = f"""
(function () {{
  var cada = {REFRESCO} * 1000;
  var titulo = document.title;
  function oculto() {{ return localStorage.getItem('{CLAVE}') === '1'; }}
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
      ojo.title = si ? 'Enseñar cifras' : 'Ocultar cifras';
      ojo.textContent = si ? '🙈' : '👁';
    }}
  }}
  document.addEventListener('click', function (e) {{
    if (e.target.closest('.ojo')) {{
      localStorage.setItem('{CLAVE}', oculto() ? '0' : '1');
      tapar();
    }} else if (e.target.closest('.estado')) {{
      refrescar();
    }}
  }});
  tapar();
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
        titulo = nuevo.title;
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
  // Con la pestaña de fondo no pido nada; al volver, si toca, refresco al momento.
  setInterval(function () {{ if (!document.hidden) refrescar(); }}, cada);
  document.addEventListener('visibilitychange', function () {{
    if (!document.hidden && Date.now() - ultimo >= cada) refrescar();
  }});
}})();
"""
