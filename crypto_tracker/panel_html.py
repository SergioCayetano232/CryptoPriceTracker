"""La página del panel. Los datos vienen hechos de panel.py."""

from datetime import datetime
from html import escape

from . import __version__
from .mensajes.base import SIMBOLOS, _num, describir
from .panel import PUNTOS_GRAFICA, Alerta, Fila, Panel, Vigilada, hace, muestrear, trazo

# Cada cuánto se refresca sola, en segundos. Los precios no cambian más rápido.
REFRESCO = 60

ANCHO, ALTO = 600, 180
MINI_ANCHO, MINI_ALTO = 100, 28


def _nombre(coin_id: str) -> str:
    return escape(coin_id.replace("-", " ").title())


def _dinero(valor: float | None, moneda: str) -> str:
    if valor is None:
        return "—"
    simbolo = SIMBOLOS.get(moneda, moneda.upper() + " ")
    signo = "-" if valor < 0 else ""
    return f"{signo}{simbolo}{_num(abs(valor))}"


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


def _cabecera(p: Panel, ahora: datetime, parado: bool) -> str:
    estado = "parado" if parado else "vivo"
    aviso = (
        '<span class="estado__texto">El bot no guarda precios desde '
        f"{hace(p.actualizado, ahora)}. ¿Está encendido?</span>"
        if parado
        else f'<span class="estado__texto">Actualizado {hace(p.actualizado, ahora)}'
        "</span>"
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
    <span class="estado estado--{estado}">
      <span class="estado__punto"></span>{aviso}
    </span>
  </div>
  <p class="etiqueta">Tu cartera</p>
  {grande}
  {detalle}
</header>"""


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
  <div class="grafica__ejes">
    <span>{_dinero(max(valores), p.moneda)}</span>
    <span>{_dinero(min(valores), p.moneda)}</span>
  </div>
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
        f'<span class="num num--{tono}">{_dinero(f.ganancia, moneda)}'
        f"<small>{_pct(f.porcentaje)}</small></span>"
        if f.ganancia is not None
        else '<span class="num num--neutro">—<small>sin coste</small></span>'
    )
    return f"""
<li class="fila">
  <div class="fila__nombre">
    <strong>{_nombre(f.coin_id)}</strong>
    <small>{_cantidad(f.cantidad)} · {_dinero(f.precio, moneda)}</small>
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


def _cartera(p: Panel) -> str:
    if not p.filas:
        return ""
    filas = "".join(_fila(f, p.moneda) for f in p.filas)
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
  <span class="num" data-k="p-{escape(v.coin_id)}">{_dinero(v.precio, moneda)}
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
      {_dinero(a.objetivo, moneda)}</strong>
    <small>#{a.id} · ahora {_dinero(a.precio, moneda)}</small>{nota}
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
<title>Tu cartera · CryptoPriceTracker</title>
<style>{CSS}</style>
</head>
<body>
<main class="panel">{contenido}</main>
<footer class="pie">
  CryptoPriceTracker {escape(__version__)} · se actualiza sola cada minuto ·
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

.marca { font-weight: 700; letter-spacing: -0.01em; }

.estado {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--suave);
}

.estado__punto {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--sube);
  box-shadow: 0 0 0 0 var(--sube);
  animation: pulso 2.4s ease-out infinite;
}

.estado--parado .estado__punto { background: var(--aviso); animation: none; }
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

.total, .num, .pastilla, .grafica__ejes, .grafica__fechas, .fila small {
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

.grafica__ejes {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: space-between;
  font-size: 12px;
  color: var(--suave);
  pointer-events: none;
}

.grafica__ejes span {
  padding: 2px 8px;
  border-radius: 8px;
  background: var(--cristal);
}

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

@media (max-width: 760px) {
  .panel { grid-template-columns: minmax(0, 1fr); gap: 14px; padding-top: 18px; }
  .tarjeta, .cabecera { padding: 18px; }
  .fila { grid-template-columns: minmax(0, 1fr) auto; gap: 4px 12px; }
  .fila .mini { display: none; }
  .fila .peso { grid-column: 1 / -1; flex-direction: row; align-items: center; }
  .fila .peso__barra { flex: 1; }
  .lista--cartera .fila > .num:nth-of-type(2) { grid-column: 2; }
  .grafica svg { height: 150px; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important;
    transition: none !important;
  }
}
"""

CSS = CSS.replace("__GRANO__", GRANO)

JS = f"""
(function () {{
  var cada = {REFRESCO} * 1000;
  function cifras(raiz) {{
    var mapa = {{}};
    raiz.querySelectorAll('[data-k]').forEach(function (el) {{
      mapa[el.dataset.k] = el.textContent.trim();
    }});
    return mapa;
  }}
  function refrescar() {{
    fetch(location.href, {{ cache: 'no-store' }})
      .then(function (r) {{ return r.ok ? r.text() : Promise.reject(r.status); }})
      .then(function (html) {{
        var nuevo = new DOMParser().parseFromString(html, 'text/html');
        var antes = cifras(document);
        document.documentElement.classList.add('recargado');
        document.querySelector('main').replaceWith(nuevo.querySelector('main'));
        document.querySelectorAll('[data-k]').forEach(function (el) {{
          var k = el.dataset.k;
          if (k in antes && antes[k] !== el.textContent.trim()) {{
            el.classList.add('latido');
          }}
        }});
      }})
      // Si el panel se ha caído, se queda lo último que había.
      .catch(function () {{}});
  }}
  setInterval(refrescar, cada);
}})();
"""
