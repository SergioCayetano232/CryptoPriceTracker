"""Dibuja la grafica de precios que se manda por Telegram."""

import io
from datetime import datetime

from .alerts import SIMBOLOS, _num
from .calendario import Mes, semanas
from .mes import MESES
from .periodo import nombre as nombre_periodo
from .reparto import Trozo

VERDE = "#16a34a"
ROJO = "#dc2626"
TEXTO = "#0f172a"
SUAVE = "#64748b"
REJILLA = "#e2e8f0"
FONDO = "#ffffff"


# Para /reparto. Comprobados para daltonismo; el orden es fijo, no se reparten al azar.
PALETA = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300")
GRIS = "#94a3b8"


class GraficaError(Exception):
    """No se pudo dibujar. Casi siempre es que falta matplotlib."""


def dibujar(
    coin_id: str,
    serie: list[tuple[datetime, float]],
    currency: str,
    horas: float,
    titulo: str | None = None,
    invertido: float | None = None,
    subtitulo: str | None = None,
) -> bytes:
    """Devuelve el PNG de la serie, que va del precio mas viejo al de ahora.

    invertido dibuja una linea discontinua con lo que te costo, para la cartera.
    """
    # Import aqui dentro: si el servidor aun no tiene matplotlib, el bot sigue
    # funcionando y /historico manda texto como antes.
    try:
        from matplotlib import dates as mdates
        from matplotlib.figure import Figure
        from matplotlib.ticker import FuncFormatter
    except ImportError as e:
        raise GraficaError(
            "Falta matplotlib. Ejecuta: pip install -r requirements.txt"
        ) from e

    if len(serie) < 2:
        raise GraficaError("Hacen falta al menos dos precios para dibujar")

    fechas = [f.astimezone() for f, _ in serie]
    precios = [p for _, p in serie]
    ahora, primero = precios[-1], precios[0]
    techo, suelo = max(precios), min(precios)
    variacion = (ahora - primero) / primero * 100 if primero else 0.0
    color = VERDE if ahora >= primero else ROJO
    detalle = f"{variacion:+.2f}%"
    # En la cartera importa si ganas o pierdes, no cuanto subio en el tramo:
    # un +50% en verde estando por debajo de lo invertido engaña.
    if invertido:
        variacion = (ahora - invertido) / invertido * 100
        color = VERDE if ahora >= invertido else ROJO
        detalle = f"{variacion:+.2f}% sobre lo invertido"
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")

    # Lo invertido tiene que verse aunque quede lejos: es justo lo que interesa.
    alto = max(techo, invertido) if invertido else techo
    bajo = min(suelo, invertido) if invertido else suelo

    # Aire arriba y abajo para que las etiquetas del maximo y minimo quepan.
    margen = (alto - bajo) * 0.18 or abs(alto) * 0.01 or 1

    fig = Figure(figsize=(8, 4.5), dpi=150, facecolor=FONDO)
    izquierda = _margen_eje(alto + margen)
    ax = fig.add_axes((izquierda, 0.1, 0.94 - izquierda, 0.67))
    ax.set_facecolor(FONDO)
    ax.set_ylim(bajo - margen, alto + margen)

    # Con miles de puntos una linea gruesa se emborrona.
    grosor = 2.2 if horas <= 48 else 1.4
    ax.plot(fechas, precios, color=color, linewidth=grosor, solid_capstyle="round")
    ax.fill_between(
        fechas, precios, bajo - margen, color=color, alpha=0.10, linewidth=0
    )

    if invertido:
        ax.axhline(invertido, color=SUAVE, linewidth=1, linestyle=(0, (4, 3)))
        ax.annotate(
            f"Invertido {simbolo}{_num(invertido)}",
            (0, invertido),
            xycoords=("axes fraction", "data"),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=8,
            color=SUAVE,
        )

    if techo != suelo:
        for precio, arriba in ((techo, True), (suelo, False)):
            i = precios.index(precio)
            ax.scatter([fechas[i]], [precio], s=16, color=color, zorder=3)
            ax.annotate(
                f"{simbolo}{_num(precio)}",
                (fechas[i], precio),
                xytext=(0, 7 if arriba else -7),
                textcoords="offset points",
                ha="center",
                va="bottom" if arriba else "top",
                fontsize=8,
                color=SUAVE,
            )

    ax.scatter(
        [fechas[-1]], [ahora], s=46, color=color, edgecolors=FONDO, lw=2, zorder=4
    )

    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(REJILLA)
    ax.grid(axis="y", color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=SUAVE, labelsize=8, length=0, pad=6)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _eje(v)))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=7))
    # Sin tz, matplotlib pinta las horas en UTC y no cuadran con tu reloj.
    ax.xaxis.set_major_formatter(
        mdates.DateFormatter(_formato_eje(horas), tz=fechas[-1].tzinfo)
    )
    ax.margins(x=0.01)

    nombre = titulo or coin_id.replace("-", " ").title()
    fig.text(0.08, 0.89, nombre, fontsize=16, weight="bold", color=TEXTO)
    periodo = subtitulo or nombre_periodo(horas)
    fig.text(0.08, 0.83, periodo[0].upper() + periodo[1:], fontsize=9, color=SUAVE)
    fig.text(
        0.94,
        0.89,
        f"{simbolo}{_num(ahora)}",
        fontsize=16,
        weight="bold",
        color=TEXTO,
        ha="right",
    )
    fig.text(
        0.94,
        0.83,
        detalle,
        fontsize=10,
        weight="bold",
        color=color,
        ha="right",
    )

    salida = io.BytesIO()
    fig.savefig(salida, format="png", facecolor=FONDO)
    return salida.getvalue()


def dibujar_reparto(trozos: list[Trozo], total: float, currency: str) -> bytes:
    """Una barra repartida entre las criptos y, debajo, una fila por cada una."""
    try:
        from matplotlib.figure import Figure
        from matplotlib.patches import Rectangle
    except ImportError as e:
        raise GraficaError(
            "Falta matplotlib. Ejecuta: pip install -r requirements.txt"
        ) from e

    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    alto = 2.05 + 0.42 * len(trozos)
    fig = Figure(figsize=(8, alto), dpi=150, facecolor=FONDO)

    # Todo en pulgadas desde arriba, para que no dependa de cuántas filas haya.
    def y(pulgadas: float) -> float:
        return 1 - pulgadas / alto

    fig.text(0.06, y(0.55), "Tu cartera", fontsize=16, weight="bold", color=TEXTO)
    fig.text(
        0.94,
        y(0.55),
        f"{simbolo}{_num(total)}",
        fontsize=16,
        weight="bold",
        color=TEXTO,
        ha="right",
    )

    ax = fig.add_axes((0.06, y(1.35), 0.88, 0.45 / alto))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 1)
    ax.axis("off")
    inicio = 0.0
    for t in trozos:
        color = GRIS if t.color is None else PALETA[t.color]
        # El borde blanco deja un hueco entre trozos, que se distingan sin color.
        ax.add_patch(
            Rectangle((inicio, 0), t.peso, 1, facecolor=color, edgecolor=FONDO, lw=2)
        )
        inicio += t.peso

    for i, t in enumerate(trozos):
        fila = y(1.85 + 0.42 * i)
        color = GRIS if t.color is None else PALETA[t.color]
        nombre = t.coin_id.replace("-", " ").title()
        # Un cuadrado de 0,16 pulgadas, centrado en la fila
        fig.patches.append(
            Rectangle(
                (0.06, fila - 0.08 / alto),
                0.16 / 8,
                0.16 / alto,
                facecolor=color,
                transform=fig.transFigure,
                figure=fig,
            )
        )
        fig.text(0.09, fila, nombre, fontsize=11, color=TEXTO, va="center")
        fig.text(
            0.72,
            fila,
            f"{t.peso:.0f}%",
            fontsize=11,
            weight="bold",
            color=TEXTO,
            va="center",
            ha="right",
        )
        fig.text(
            0.94,
            fila,
            f"{simbolo}{_num(t.valor)}",
            fontsize=11,
            color=SUAVE,
            va="center",
            ha="right",
        )

    salida = io.BytesIO()
    fig.savefig(salida, format="png", facecolor=FONDO)
    return salida.getvalue()


# Un día que se mueve esto o más sale con el color a tope.
TOPE_CALENDARIO = 5
# Entre el gris de "sin precio" y el de las letras, que se distinga de los dos.
IGUAL = "#cbd5e1"
DIAS_SEMANA = ("L", "M", "X", "J", "V", "S", "D")


def dibujar_calendario(coin_id: str, m: Mes) -> bytes:
    """El mes en casillas de lunes a domingo, cada día en verde o en rojo."""
    try:
        from matplotlib.figure import Figure
        from matplotlib.patches import FancyBboxPatch
    except ImportError as e:
        raise GraficaError(
            "Falta matplotlib. Ejecuta: pip install -r requirements.txt"
        ) from e

    filas = semanas(m)
    alto = 1.3 + 0.95 * len(filas)
    fig = Figure(figsize=(8, alto), dpi=150, facecolor=FONDO)

    def y(pulgadas: float) -> float:
        return 1 - pulgadas / alto

    nombre = coin_id.replace("-", " ").title()
    fig.text(0.06, y(0.5), nombre, fontsize=16, weight="bold", color=TEXTO)
    fig.text(0.06, y(0.82), f"{MESES[m.mes - 1]} de {m.año}", fontsize=10, color=SUAVE)
    if m.cambio is not None:
        color = VERDE if m.cambio >= 0 else ROJO
        pct = f"{m.cambio:+.1f}%".replace(".", ",")
        fig.text(0.94, y(0.5), pct, fontsize=16, weight="bold", color=color, ha="right")
        fig.text(0.94, y(0.82), "en el mes", fontsize=10, color=SUAVE, ha="right")

    ax = fig.add_axes((0.06, 0.2 / alto, 0.88, (alto - 1.25) / alto))
    ax.set_xlim(0, 7)
    ax.set_ylim(len(filas), -0.35)
    ax.axis("off")
    for col, letra in enumerate(DIAS_SEMANA):
        ax.text(col + 0.5, -0.12, letra, ha="center", fontsize=10, color=SUAVE)

    for fila, semana in enumerate(filas):
        for col, c in enumerate(semana):
            if c is None:
                continue
            fondo, borde, letra = _casilla(c.cambio, c.futuro)
            ax.add_patch(
                FancyBboxPatch(
                    (col + 0.06, fila + 0.06),
                    0.88,
                    0.88,
                    boxstyle="round,pad=0,rounding_size=0.12",
                    facecolor=fondo,
                    edgecolor=borde,
                    lw=1,
                )
            )
            ax.text(col + 0.16, fila + 0.27, str(c.dia.day), fontsize=8, color=letra)
            if c.cambio is not None:
                pct = f"{c.cambio:+.1f}%".replace(".", ",") if c.cambio else "0,0%"
                ax.text(
                    col + 0.5,
                    fila + 0.62,
                    pct,
                    ha="center",
                    fontsize=9,
                    weight="bold",
                    color=letra,
                )

    salida = io.BytesIO()
    fig.savefig(salida, format="png", facecolor=FONDO)
    return salida.getvalue()


def _casilla(cambio: float | None, futuro: bool) -> tuple[str, str, str]:
    """(fondo, borde, letra) de un día."""
    if futuro:
        return FONDO, REJILLA, GRIS
    if cambio is None:
        return REJILLA, REJILLA, SUAVE
    if cambio == 0:
        return IGUAL, IGUAL, TEXTO
    fuerza = 0.2 + 0.8 * min(abs(cambio) / TOPE_CALENDARIO, 1)
    fondo = _mezcla(VERDE if cambio > 0 else ROJO, fuerza)
    # En los suaves el blanco no se lee; a partir de media fuerza, sí.
    return fondo, fondo, FONDO if fuerza >= 0.55 else TEXTO


def _mezcla(color: str, fuerza: float) -> str:
    """El color aclarado hacia el blanco: con fuerza 1 sale tal cual."""
    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    r, g, b = (round(255 - (255 - v) * fuerza) for v in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _formato_eje(horas: float) -> str:
    # En un dia basta la hora; en una semana, la hora sola se repite y lia.
    if horas <= 24:
        return "%H:%M"
    if horas <= 72:
        return "%d/%m %Hh"
    return "%d/%m"


def _margen_eje(tope: float) -> float:
    """Hueco a la izquierda para los numeros del eje, que en un SHIB son largos."""
    # Con una cifra de mas que el tope: los del eje van mas finos que el.
    largo = len(_eje(tope)) + 1
    return max(0.08, 0.01 + largo * 0.0095)


def _eje(valor: float) -> str:
    # En el eje sobran los decimales salvo en las criptos de centimos.
    if abs(valor) >= 100:
        return f"{valor:,.0f}".replace(",", ".")
    return _num(valor)
