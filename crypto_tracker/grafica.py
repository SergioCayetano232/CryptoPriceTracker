"""Dibuja la grafica de precios que se manda por Telegram."""

import io
from datetime import datetime

from .alerts import SIMBOLOS, _num
from .periodo import nombre as nombre_periodo

VERDE = "#16a34a"
ROJO = "#dc2626"
TEXTO = "#0f172a"
SUAVE = "#64748b"
REJILLA = "#e2e8f0"
FONDO = "#ffffff"


class GraficaError(Exception):
    """No se pudo dibujar. Casi siempre es que falta matplotlib."""


def dibujar(
    coin_id: str,
    serie: list[tuple[datetime, float]],
    currency: str,
    horas: float,
    titulo: str | None = None,
    invertido: float | None = None,
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

    fig = Figure(figsize=(8, 4.5), dpi=150, facecolor=FONDO)
    ax = fig.add_axes((0.08, 0.1, 0.86, 0.67))
    ax.set_facecolor(FONDO)

    # Lo invertido tiene que verse aunque quede lejos: es justo lo que interesa.
    alto = max(techo, invertido) if invertido else techo
    bajo = min(suelo, invertido) if invertido else suelo

    # Aire arriba y abajo para que las etiquetas del maximo y minimo quepan.
    margen = (alto - bajo) * 0.18 or abs(alto) * 0.01 or 1
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
    periodo = nombre_periodo(horas)
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


def _formato_eje(horas: float) -> str:
    # En un dia basta la hora; en una semana, la hora sola se repite y lia.
    if horas <= 24:
        return "%H:%M"
    if horas <= 72:
        return "%d/%m %Hh"
    return "%d/%m"


def _eje(valor: float) -> str:
    # En el eje sobran los decimales salvo en las criptos de centimos.
    if abs(valor) >= 100:
        return f"{valor:,.0f}".replace(",", ".")
    return _num(valor)
