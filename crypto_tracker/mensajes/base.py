"""Lo que usan todos los mensajes: cómo se escriben los números, flechas y barras."""

import math

from ..condicion import Condicion
from ..config import Watch
from ..puntuales import Puntual, cumplidas
from ..telegram import escape

# Estados en los que puede estar una cripto respecto a sus umbrales.
BAJO = "bajo"  # por debajo del minimo
NORMAL = "normal"  # entre los dos umbrales
ALTO = "alto"  # por encima del maximo

SIMBOLOS = {"eur": "€", "usd": "$", "gbp": "£"}

# Satoshis en un bitcoin, para /convertir.
POR_BTC = 100_000_000

# El plan gratis de CoinGecko pide citarles, con enlace, junto a los datos.
# La frase tiene que ser una de las suyas, por eso va en ingles.
FUENTE = '<i>Price data by <a href="https://www.coingecko.com">CoinGecko</a></i>'

# De menos a mas alto, para dibujar el historico en una linea.
BARRAS = "▁▂▃▄▅▆▇█"

# Mas barritas que esto y en el movil la linea salta a la siguiente.
BARRAS_MOVIL = 24
MINIMO_BARRAS = 6

# Ni la cripto mas barata necesita mas para que se vea su precio.
MAX_DECIMALES = 12


def sparkline(precios: list[float]) -> str:
    """Dibuja los precios como una linea de barritas, del mas viejo al mas nuevo."""
    if len(precios) < 2:
        return ""

    suelo, techo = min(precios), max(precios)
    rango = techo - suelo

    # Todo al mismo precio: una linea plana a media altura, que dividir
    # por un rango de cero reventaria.
    if rango == 0:
        return BARRAS[len(BARRAS) // 2] * len(precios)

    return "".join(
        BARRAS[min(int((p - suelo) / rango * len(BARRAS)), len(BARRAS) - 1)]
        for p in precios
    )


def _veces(n: int, una: str, varias: str) -> str:
    return f"{n} {una if n == 1 else varias}"


def _decimal(valor: float) -> str:
    """1,5 o 3: un decimal, y sin él si es redondo."""
    return f"{valor:.1f}".replace(".", ",").removesuffix(",0")


def _pct(valor: float) -> str:
    return f"{valor:g}".replace(".", ",")


def _es(numero: str) -> str:
    """1,234.5 → 1.234,5"""
    return numero.replace(",", " ").replace(".", ",").replace(" ", ".")


def _hace(horas: float) -> str:
    """'hace 30 días', 'hace 12 h'."""
    if horas >= 48 and horas % 24 == 0:
        return f"hace {int(horas // 24)} días"
    return f"hace {horas:g} h".replace(".", ",")


def _nombre(coin_id: str) -> str:
    return escape(coin_id.replace("-", " ").title())


def _quien_condicion(c: Condicion) -> str:
    return "El miedo" if c.indicador == "miedo" else "El RSI"


def _signo(porcentaje: float) -> str:
    # Un -0,00001 de sumar decimales saldría "-0,0%": el + 0.0 lo deja en +0,0.
    valor = round(porcentaje, 1) + 0.0
    return f"{valor:+.1f}%".replace(".", ",")


def describir(watch: Watch, currency: str) -> str:
    """Como se vigila una cripto, en cristiano: 'cada 5 % que se mueva'."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    if watch.percent is not None:
        return f"cada {watch.percent:g} % que se mueva".replace(".", ",")
    if watch.step is not None:
        return f"cada {simbolo}{_num(watch.step)}"

    lados = []
    if watch.min_price is not None:
        lados.append(f"si baja de {simbolo}{_num(watch.min_price)}")
    if watch.max_price is not None:
        lados.append(f"si sube de {simbolo}{_num(watch.max_price)}")
    return " o ".join(lados)


def muestrear(precios: list[float], n: int) -> list[float]:
    """Se queda con n puntos repartidos, siempre con el primero y el ultimo."""
    if len(precios) <= n:
        return list(precios)

    paso = (len(precios) - 1) / (n - 1)
    return [precios[round(i * paso)] for i in range(n)]


def _siguiente(
    precio: float, arriba: float | None, abajo: float | None, simbolo: str
) -> str:
    """'↑ €64.000,00 (+1.59%) · ↓ €63.000,00 (-0.90%)'. Vacio si no hay nada."""
    # Entre ciclo y ciclo puede haberlo pasado ya; un "-52%" ahi no se entiende.
    if (arriba is not None and precio >= arriba) or (
        abajo is not None and precio < abajo
    ):
        return "Ya ha pasado su aviso, te llega en el próximo ciclo"

    lados = []
    for flecha, objetivo in (("↑", arriba), ("↓", abajo)):
        if objetivo is None or not precio:
            continue
        falta = (objetivo - precio) / precio * 100
        lados.append(f"{flecha} {simbolo}{_num(objetivo)} ({falta:+.2f}%)")
    return " · ".join(lados)


def _falta(precio: float | None, alerta: Puntual) -> str:
    """'(falta +3.20%)'. Vacio si no hay precio con el que comparar."""
    if not precio:
        return ""
    # Entre ciclo y ciclo puede haber llegado ya; saltara en el siguiente.
    if cumplidas([alerta], {alerta.coin_id: precio}):
        if alerta.condicion:
            # Aquí no miro el miedo ni el RSI: no sé si saltará ya.
            return "(ya está en el precio; falta que se cumpla lo otro)"
        return "(ya ha llegado, te aviso en el próximo ciclo)"
    return f"(falta {(alerta.objetivo - precio) / precio * 100:+.2f}%)"


def _barra_progreso(porcentaje: float) -> str:
    """'<code>▓▓▓▓▓▓▓░░░</code> 68%'."""
    # Con floor un 99% no se ve lleno, que es lo que es: aún no ha llegado.
    llenas = math.floor(porcentaje / 10)
    return f"<code>{'▓' * llenas}{'░' * (10 - llenas)}</code> {math.floor(porcentaje)}%"


def _ganancia(ganancia: float, simbolo: str) -> str:
    """'+€20,00' o '-€200,00'."""
    signo = "+" if ganancia >= 0 else "-"
    return f"{signo}{simbolo}{_num(abs(ganancia))}"


def _peso(porcentaje: float) -> str:
    # Un "0%" parece que no tienes nada; va escapado, que el mensaje es HTML.
    return f"{porcentaje:.0f}%" if porcentaje >= 1 else "&lt;1%"


def _minutos(minutos: int) -> str:
    return f"{minutos // 60} h" if minutos % 60 == 0 else f"{minutos} min"


def _flecha(variacion: float) -> str:
    return "🔺" if variacion > 0 else "🔻" if variacion < 0 else "➖"


def _num(valor: float) -> str:
    """Formatea el numero segun su tamaño: 55.500, 0,3421 o 0,00001234."""
    if abs(valor) >= 1:
        texto = f"{valor:,.2f}"
    elif valor == 0:
        texto = "0.0000"
    else:
        # Con 4 decimales fijos un SHIB salia como 0,0000. Van las que hagan
        # falta para 4 cifras, y los ceros sobrantes fuera: 0,00002 y no 0,00002000.
        cifras = -math.floor(math.log10(abs(valor))) + 3
        texto = f"{valor:.{min(max(4, cifras), MAX_DECIMALES)}f}"
        entero, decimales = texto.split(".")
        texto = f"{entero}.{decimales[:4]}{decimales[4:].rstrip('0')}"

    # De formato ingles (1,234.56) a español (1.234,56).
    return texto.replace(",", "@").replace(".", ",").replace("@", ".")
