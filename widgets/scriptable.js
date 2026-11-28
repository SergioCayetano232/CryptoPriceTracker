// Widget del panel de CryptoPriceTracker para Scriptable (iPhone y iPad).
//
// 1. Arranca el panel abierto a tu red: python main.py --panel --red
// 2. Copia aquí la dirección que te dice al arrancar, con tu PANEL_CLAVE.
// 3. En Scriptable, pega este script; luego añade un widget de Scriptable a la
//    pantalla de inicio y elige este script.
//
// Solo funciona con el móvil en la misma wifi que el ordenador del panel.

const URL = "http://192.168.1.20:8000/api.json?clave=TU_PANEL_CLAVE"

const SIMBOLOS = { eur: "€", usd: "$", gbp: "£" }
const VERDE = new Color("#3fd6a0")
const ROJO = new Color("#ff6b81")
const SUAVE = new Color("#9a94b4")

function dinero(valor, moneda) {
  const simbolo = SIMBOLOS[moneda] || moneda.toUpperCase() + " "
  const [entero, decimales] = Math.abs(valor).toFixed(2).split(".")
  const conPuntos = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".")
  return (valor < 0 ? "-" : "") + simbolo + conPuntos + "," + decimales
}

function pct(valor) {
  return (valor > 0 ? "+" : "") + valor.toFixed(2).replace(".", ",") + " %"
}

function hace(iso) {
  const minutos = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (minutos < 1) return "ahora mismo"
  if (minutos < 60) return `hace ${minutos} min`
  if (minutos < 48 * 60) return `hace ${Math.round(minutos / 60)} h`
  return `hace ${Math.round(minutos / 1440)} días`
}

function texto(widget, contenido, tamaño, color, negrita) {
  const t = widget.addText(contenido)
  t.font = negrita ? Font.boldSystemFont(tamaño) : Font.systemFont(tamaño)
  t.textColor = color
  t.minimumScaleFactor = 0.6
  t.lineLimit = 1
  return t
}

async function montar() {
  const w = new ListWidget()
  const fondo = new LinearGradient()
  fondo.colors = [new Color("#2a1660"), new Color("#0d0b16")]
  fondo.locations = [0, 1]
  w.backgroundGradient = fondo
  // iOS decide cuándo refresca; esto es solo lo que le pedimos.
  w.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000)

  let d
  const peticion = new Request(URL)
  peticion.timeoutInterval = 10
  try {
    const cuerpo = await peticion.loadString()
    if (peticion.response.statusCode === 403) {
      texto(w, "CryptoPriceTracker", 12, SUAVE, true)
      w.addSpacer(6)
      texto(w, "Clave mal puesta", 15, Color.white(), true)
      texto(w, "Revisa ?clave= en la URL", 11, SUAVE, false)
      return w
    }
    d = JSON.parse(cuerpo)
  } catch (e) {
    texto(w, "CryptoPriceTracker", 12, SUAVE, true)
    w.addSpacer(6)
    texto(w, "No llego al panel", 15, Color.white(), true)
    texto(w, "¿Misma wifi y --panel --red?", 11, SUAVE, false)
    return w
  }
  if (d.total === null || d.total === undefined) {
    texto(w, "Tu cartera", 12, SUAVE, true)
    w.addSpacer(6)
    texto(w, "Sin cartera", 18, Color.white(), true)
    return w
  }

  texto(w, "Tu cartera", 12, SUAVE, true)
  w.addSpacer(4)
  texto(w, dinero(d.total, d.moneda), 24, Color.white(), true)
  if (d.cambio_24h !== null) {
    texto(w, pct(d.cambio_24h) + " en 24 h", 13, d.cambio_24h >= 0 ? VERDE : ROJO, true)
  }
  w.addSpacer()
  // La que más se ha movido hoy, que es la que querrás mirar.
  const movidas = d.criptos.filter((c) => c.cambio_24h !== null)
  if (movidas.length) {
    movidas.sort((a, b) => Math.abs(b.cambio_24h) - Math.abs(a.cambio_24h))
    const c = movidas[0]
    const nombre = c.id.charAt(0).toUpperCase() + c.id.slice(1).replace(/-/g, " ")
    texto(w, `${nombre} ${pct(c.cambio_24h)}`, 11, c.cambio_24h >= 0 ? VERDE : ROJO, false)
  }
  const estado = d.parado ? "⚠️ el bot está parado" : hace(d.actualizado)
  texto(w, estado, 10, d.parado ? new Color("#ffb648") : SUAVE, false)
  return w
}

const widget = await montar()
if (config.runsInWidget) {
  Script.setWidget(widget)
} else {
  await widget.presentSmall()
}
Script.complete()
