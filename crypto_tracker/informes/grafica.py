"""Dibuja la grafica de precios que se manda por Telegram."""

import io
from datetime import datetime

from ..alerts import SIMBOLOS, _num
from ..arcoiris import FRANJAS, Arcoiris
from ..calendario import Mes, semanas
from ..correlacion import Matriz
from ..mapa import Mapa, repartir
from ..nucleo.periodo import nombre as nombre_periodo
from ..nucleo.simbolos import de_id
from ..reparto import OTRAS, Trozo
from ..velas import Vela
from .mes import MESES
from .tarjeta import Tarjeta
from .tarjeta_anual import TarjetaAnual

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
        tramo = (fechas[-1] - fechas[0]).total_seconds()
        for precio, arriba in ((techo, True), (suelo, False)):
            i = precios.index(precio)
            ax.scatter([fechas[i]], [precio], s=16, color=color, zorder=3)
            donde = (fechas[i] - fechas[0]).total_seconds() / tramo if tramo else 0.5
            ax.annotate(
                f"{simbolo}{_num(precio)}",
                (fechas[i], precio),
                xytext=(0, 7 if arriba else -7),
                textcoords="offset points",
                ha=_alineacion(donde),
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
    periodo = subtitulo or nombre_periodo(horas)
    _cabecera(fig, nombre, periodo, f"{simbolo}{_num(ahora)}", detalle, color)

    salida = io.BytesIO()
    fig.savefig(salida, format="png", facecolor=FONDO)
    return salida.getvalue()


def _cabecera(fig, nombre: str, periodo: str, precio: str, detalle: str, color: str):
    """El nombre y el tramo a la izquierda; el precio y el % a la derecha."""
    fig.text(0.08, 0.89, nombre, fontsize=16, weight="bold", color=TEXTO)
    fig.text(0.08, 0.83, periodo[0].upper() + periodo[1:], fontsize=9, color=SUAVE)
    fig.text(0.94, 0.89, precio, fontsize=16, weight="bold", color=TEXTO, ha="right")
    fig.text(0.94, 0.83, detalle, fontsize=10, weight="bold", color=color, ha="right")


def dibujar_velas(
    coin_id: str, velas: list[Vela], cada: int, currency: str, horas: float
) -> bytes:
    """Como dibujar(), pero en velas: verde si cerró por encima de donde abrió."""
    try:
        from matplotlib.figure import Figure
        from matplotlib.ticker import FuncFormatter
    except ImportError as e:
        raise GraficaError(
            "Falta matplotlib. Ejecuta: pip install -r requirements.txt"
        ) from e

    if not velas:
        raise GraficaError("No hay velas que dibujar")

    primero, ahora = velas[0].apertura, velas[-1].cierre
    techo = max(v.alto for v in velas)
    suelo = min(v.bajo for v in velas)
    variacion = (ahora - primero) / primero * 100 if primero else 0.0
    color = VERDE if ahora >= primero else ROJO
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    margen = (techo - suelo) * 0.12 or abs(techo) * 0.01 or 1

    fig = Figure(figsize=(8, 4.5), dpi=150, facecolor=FONDO)
    izquierda = _margen_eje(techo + margen)
    ax = fig.add_axes((izquierda, 0.1, 0.94 - izquierda, 0.67))
    ax.set_facecolor(FONDO)
    ax.set_ylim(suelo - margen, techo + margen)

    # Una detrás de otra, sin dejar hueco donde no hay precios, como en los
    # exchanges: con días sueltos en 90 días salían rayitas perdidas.
    ancho = 0.7
    for x, v in enumerate(velas):
        tono = VERDE if v.sube else ROJO
        ax.vlines(x, v.bajo, v.alto, color=tono, linewidth=1)
        alto_cuerpo = abs(v.cierre - v.apertura) or (techo - suelo) * 0.002
        ax.bar(
            x,
            alto_cuerpo,
            bottom=min(v.apertura, v.cierre),
            width=ancho,
            color=tono,
            linewidth=0,
            zorder=3,
        )

    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(REJILLA)
    ax.grid(axis="y", color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=SUAVE, labelsize=8, length=0, pad=6)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _eje(v)))
    marcas = list(range(0, len(velas), max(1, round(len(velas) / 6))))
    ax.set_xticks(
        marcas, [velas[i].inicio.strftime(_formato_eje(horas)) for i in marcas]
    )
    ax.set_xlim(-0.7, len(velas) - 0.3)

    tramo = "1 hora" if cada == 1 else "1 día" if cada == 24 else f"{cada} horas"
    _cabecera(
        fig,
        coin_id.replace("-", " ").title(),
        f"{nombre_periodo(horas)} · cada vela, {tramo}",
        f"{simbolo}{_num(ahora)}",
        f"{variacion:+.2f}%",
        color,
    )
    salida = io.BytesIO()
    fig.savefig(salida, format="png", facecolor=FONDO)
    return salida.getvalue()


def dibujar_comparar(
    lineas: list[tuple[str, list[tuple[datetime, float]]]], horas: float
) -> bytes:
    """/comparar: todas las series empezando en 100, de mejor a peor."""
    try:
        from matplotlib import dates as mdates
        from matplotlib.figure import Figure
        from matplotlib.ticker import FuncFormatter
    except ImportError as e:
        raise GraficaError(
            "Falta matplotlib. Ejecuta: pip install -r requirements.txt"
        ) from e

    if not lineas or len(lineas) > len(PALETA):
        raise GraficaError(f"Dibujo de 1 a {len(PALETA)} criptos")

    valores = [v for _, serie in lineas for _, v in serie]
    alto, bajo = max(valores + [100]), min(valores + [100])
    margen = (alto - bajo) * 0.12 or 1

    fig = Figure(figsize=(8, 4.5), dpi=150, facecolor=FONDO)
    # A la derecha queda sitio para el nombre de cada una.
    ax = fig.add_axes((0.09, 0.1, 0.68, 0.67))
    ax.set_facecolor(FONDO)
    ax.set_ylim(bajo - margen, alto + margen)
    ax.axhline(100, color=SUAVE, linewidth=1, linestyle=(0, (4, 3)))

    grosor = 2 if horas <= 48 else 1.4
    finales = []
    for (coin_id, serie), color in zip(lineas, PALETA, strict=False):
        fechas = [f.astimezone() for f, _ in serie]
        ax.plot(
            fechas,
            [v for _, v in serie],
            color=color,
            linewidth=grosor,
            solid_capstyle="round",
        )
        ax.scatter(
            [fechas[-1]],
            [serie[-1][1]],
            s=30,
            color=color,
            edgecolors=FONDO,
            lw=1.5,
            zorder=4,
        )
        finales.append((serie[-1][1], coin_id, color))

    # Si dos acaban casi igual, sus nombres se pisarían: los separo un poco.
    hueco = (alto - bajo + 2 * margen) * 0.075
    finales.sort()
    puestos: list[float] = []
    for final, _, _ in finales:
        puestos.append(max(final, puestos[-1] + hueco) if puestos else final)
    # Si al empujar hacia arriba se salen, los bajo todos lo que sobre.
    sobra = puestos[-1] - (alto + margen)
    if sobra > 0:
        puestos = [p - sobra for p in puestos]

    for (final, coin_id, color), y in zip(finales, puestos, strict=True):
        ax.annotate(
            f"{_corto(coin_id)}  {final - 100:+.1f}%".replace(".", ","),
            (1, y),
            xycoords=("axes fraction", "data"),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
            weight="bold",
            color=color,
            annotation_clip=False,
        )

    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(REJILLA)
    ax.grid(axis="y", color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=SUAVE, labelsize=8, length=0, pad=6)
    # En el eje, lo que ha subido o bajado; el 100 de la base no le dice nada a nadie.
    decimales = 1 if alto - bajo < 4 else 0
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda v, _: _pct_eje(v - 100, decimales))
    )
    ultima = lineas[0][1][-1][0].astimezone()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=7))
    ax.xaxis.set_major_formatter(
        mdates.DateFormatter(_formato_eje(horas), tz=ultima.tzinfo)
    )
    ax.margins(x=0.01)

    fig.text(0.09, 0.89, "Cómo les ha ido", fontsize=16, weight="bold", color=TEXTO)
    periodo = nombre_periodo(horas)
    fig.text(0.09, 0.83, periodo[0].upper() + periodo[1:], fontsize=9, color=SUAVE)

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


# La tarjeta va en oscuro: en el móvil y en las redes se ve más que una blanca.
NOCHE = "#0b1220"
CLARO = "#f8fafc"
APAGADO = "#94a3b8"
VERDE_NOCHE = "#4ade80"
ROJO_NOCHE = "#f87171"


def dibujar_tarjeta(t: Tarjeta) -> bytes:
    """Cuadrada, para mandarla tal cual. Sin una sola cifra en dinero."""
    try:
        import numpy as np
        from matplotlib.figure import Figure
    except ImportError as e:
        raise GraficaError(
            "Falta matplotlib. Ejecuta: pip install -r requirements.txt"
        ) from e

    grande = t.total if t.total is not None else t.tramo
    if grande is None:
        raise GraficaError("No hay ningún % que enseñar")
    color = VERDE_NOCHE if grande >= 0 else ROJO_NOCHE

    fig = Figure(figsize=(7.2, 7.2), dpi=150, facecolor=NOCHE)
    _brillo(fig, np, color)

    fig.text(0.08, 0.92, "MI CARTERA CRIPTO", fontsize=11, weight="bold", color=APAGADO)
    fig.text(0.92, 0.92, f"{t.dia:%d/%m/%Y}", fontsize=11, color=APAGADO, ha="right")
    fig.text(0.075, 0.76, _pct_tarjeta(grande), fontsize=62, weight="bold", color=color)
    if t.total is not None:
        debajo = "sobre lo que he metido"
    else:
        debajo = _en_el_tramo(t.horas)
    fig.text(0.08, 0.70, debajo, fontsize=13, color=CLARO)

    if len(t.linea) >= 2:
        if t.total is not None and t.tramo is not None:
            fig.text(
                0.08,
                0.62,
                f"{_pct_tarjeta(t.tramo)} {_en_el_tramo(t.horas)}",
                fontsize=11,
                color=APAGADO,
            )
        _linea_tarjeta(fig, t.linea)

    if t.reparto:
        _reparto_tarjeta(fig, t.reparto)

    fig.text(
        0.5,
        0.04,
        "Solo porcentajes, sin cifras · CryptoPriceTracker",
        fontsize=8,
        color=APAGADO,
        ha="center",
        alpha=0.7,
    )
    salida = io.BytesIO()
    fig.savefig(salida, format="png", facecolor=NOCHE)
    return salida.getvalue()


# Lo que se mueve en un día una de las grandes: de ahí para arriba, color a tope.
TOPE_MAPA = 8
QUIETA = "#334155"
VERDE_MAPA = "#15803d"
ROJO_MAPA = "#b91c1c"
# Por debajo de este tamaño de letra ya no se lee: mejor el recuadro sin nada.
LETRA_MINIMA = 6


def dibujar_mapa(m: Mapa, mias: set[str]) -> bytes:
    """Un recuadro por cripto, del tamaño de lo que vale y del color de su día."""
    try:
        from matplotlib.figure import Figure
        from matplotlib.patches import Rectangle
    except ImportError as e:
        raise GraficaError(
            "Falta matplotlib. Ejecuta: pip install -r requirements.txt"
        ) from e

    ancho, alto = 8.0, 8.6
    fig = Figure(figsize=(ancho, alto), dpi=150, facecolor=NOCHE)
    color = VERDE_NOCHE if m.media >= 0 else ROJO_NOCHE
    fig.text(0.04, 0.955, "El mercado hoy", fontsize=17, weight="bold", color=CLARO)
    fig.text(
        0.96,
        0.955,
        _pct_tarjeta(m.media),
        fontsize=17,
        weight="bold",
        color=color,
        ha="right",
    )
    debajo = (
        f"Las {len(m.casillas)} más grandes en 24 h, cada una del tamaño de lo que vale"
    )
    fig.text(0.04, 0.927, debajo, fontsize=9, color=APAGADO)
    if mias & {c.coin_id for c in m.casillas}:
        fig.text(
            0.96, 0.927, "Con borde, las tuyas", fontsize=9, color=APAGADO, ha="right"
        )

    # En pulgadas, para que repartir saque cuadrados de verdad y no estirados.
    izq, abajo, w, h = 0.3, 0.3, ancho - 0.6, alto * 0.9 - 0.35
    ax = fig.add_axes((izq / ancho, abajo / alto, w / ancho, h / alto))
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)
    ax.axis("off")

    rects = repartir([c.capital for c in m.casillas], w, h)
    for c, (x, y, cw, ch) in zip(m.casillas, rects, strict=True):
        ax.add_patch(
            Rectangle(
                (x, y),
                cw,
                ch,
                facecolor=_color_mapa(c.variacion),
                edgecolor=NOCHE,
                lw=1.5,
            )
        )
        if c.coin_id in mias:
            hueco = 0.04
            ax.add_patch(
                Rectangle(
                    (x + hueco, y + hueco),
                    cw - 2 * hueco,
                    ch - 2 * hueco,
                    fill=False,
                    edgecolor=CLARO,
                    lw=1.6,
                )
            )

        # Que el nombre quepa a lo ancho y, con el % debajo, a lo alto.
        letra = min(30, ch * 72 / 3.2, cw * 0.75 * 72 / (0.68 * max(len(c.simbolo), 3)))
        if letra < LETRA_MINIMA:
            continue
        cabe_pct = letra * 0.62 >= LETRA_MINIMA
        ax.text(
            x + cw / 2,
            y + ch / 2,
            c.simbolo,
            fontsize=letra,
            weight="bold",
            color=CLARO,
            ha="center",
            va="bottom" if cabe_pct else "center",
        )
        if not cabe_pct:
            continue
        ax.text(
            x + cw / 2,
            y + ch / 2 + 0.02,
            _pct_tarjeta(c.variacion),
            fontsize=letra * 0.62,
            color=CLARO,
            ha="center",
            va="top",
        )

    salida = io.BytesIO()
    fig.savefig(salida, format="png", facecolor=NOCHE)
    return salida.getvalue()


# De abajo arriba, del azul de "casi regalado" al granate de "burbuja máxima".
COLORES_ARCOIRIS = (
    "#3b4cc0",
    "#4f8fd6",
    "#36b3a0",
    "#5cb85c",
    "#c9d64a",
    "#f2c94c",
    "#f2994a",
    "#e05a47",
    "#b81d52",
)
# Un año más allá de hoy, para ver hacia dónde van las franjas.
ADELANTE = 365


def dibujar_arcoiris(a: Arcoiris) -> bytes:
    """El precio de bitcoin encima de las nueve franjas, en escala logarítmica."""
    try:
        from datetime import timedelta

        from matplotlib.dates import DateFormatter, YearLocator
        from matplotlib.figure import Figure
        from matplotlib.ticker import FuncFormatter
    except ImportError as e:
        raise GraficaError(
            "Falta matplotlib. Ejecuta: pip install -r requirements.txt"
        ) from e

    hoy, precio = a.hoy
    primero = a.dias[0][0]
    fechas = [
        primero + timedelta(days=i) for i in range((hoy - primero).days + ADELANTE + 1)
    ]
    curva = [a.curva(f) for f in fechas]

    fig = Figure(figsize=(8, 6.2), dpi=150, facecolor=NOCHE)
    franja = a.franja
    fig.text(
        0.06, 0.94, "Bitcoin en el arcoíris", fontsize=16, weight="bold", color=CLARO
    )
    fig.text(
        0.94,
        0.94,
        FRANJAS[franja],
        fontsize=14,
        weight="bold",
        color=COLORES_ARCOIRIS[franja],
        ha="right",
    )
    fig.text(
        0.06,
        0.905,
        f"Desde {primero.year}, contra su curva de largo plazo · escala logarítmica",
        fontsize=9,
        color=APAGADO,
    )

    ax = fig.add_axes((0.11, 0.1, 0.85, 0.76), facecolor=NOCHE)
    for i, color in enumerate(COLORES_ARCOIRIS):
        abajo = [c * 10 ** a.bordes[i] for c in curva]
        arriba = [c * 10 ** a.bordes[i + 1] for c in curva]
        ax.fill_between(fechas, abajo, arriba, color=color, alpha=0.75, lw=0)
    ax.plot([d for d, _ in a.dias], [p for _, p in a.dias], color=CLARO, lw=1.1)
    ax.plot([hoy], [precio], "o", color=CLARO, markersize=6, markeredgecolor=NOCHE)

    ax.set_yscale("log")
    ax.set_xlim(fechas[0], fechas[-1])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _dolares_eje(v)))
    ax.yaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))
    ax.xaxis.set_major_locator(YearLocator(2))
    ax.xaxis.set_major_formatter(DateFormatter("%Y"))
    ax.tick_params(colors=APAGADO, labelsize=8)
    ax.tick_params(which="minor", length=0)
    for lado in ax.spines.values():
        lado.set_visible(False)
    ax.grid(axis="y", color=APAGADO, alpha=0.15, lw=0.6)

    salida = io.BytesIO()
    fig.savefig(salida, format="png", facecolor=NOCHE)
    return salida.getvalue()


def _dolares_eje(valor: float) -> str:
    if valor >= 1000:
        return f"${valor / 1000:,.0f}k".replace(",", ".")
    return f"${valor:,.0f}"


def _color_mapa(variacion: float) -> str:
    if variacion == 0:
        return QUIETA
    fuerza = 0.3 + 0.7 * min(abs(variacion) / TOPE_MAPA, 1)
    return _hacia(QUIETA, VERDE_MAPA if variacion > 0 else ROJO_MAPA, fuerza)


def _hacia(desde: str, hasta: str, fuerza: float) -> str:
    """De un color a otro: con fuerza 1 sale el segundo tal cual."""
    a = [int(desde[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(hasta[i : i + 2], 16) for i in (1, 3, 5)]
    r, g, bl = (round(x + (y - x) * fuerza) for x, y in zip(a, b, strict=True))
    return f"#{r:02x}{g:02x}{bl:02x}"


# Los extremos de /correlacion todas: al revés en azul, a la vez en naranja.
JUNTAS = "#eb6834"
AL_REVES = "#2a78d6"


def dibujar_correlaciones(m: Matriz, periodo: str) -> bytes:
    """Todas contra todas, con el número en cada casilla."""
    try:
        from matplotlib.figure import Figure
        from matplotlib.patches import Rectangle
    except ImportError as e:
        raise GraficaError(
            "Falta matplotlib. Ejecuta: pip install -r requirements.txt"
        ) from e

    # En pulgadas: con 3 o con 8 criptos, los márgenes no cambian.
    n = len(m.ids)
    rejilla = 0.75 * n
    ancho = max(5.6, 1.4 + rejilla)
    alto = 1.3 + rejilla + 0.6
    fig = Figure(figsize=(ancho, alto), dpi=150, facecolor=FONDO)
    fig.text(
        0.3 / ancho,
        1 - 0.25 / alto,
        "Cómo se mueven juntas",
        fontsize=14,
        weight="bold",
        color=TEXTO,
        va="top",
    )
    fig.text(
        0.3 / ancho,
        1 - 0.6 / alto,
        periodo.capitalize(),
        fontsize=10,
        color=SUAVE,
        va="top",
    )
    ax = fig.add_axes((1.1 / ancho, 0.6 / alto, rejilla / ancho, rejilla / alto))
    nombres = [_corto(c) for c in m.ids]
    for fila, una in enumerate(m.ids):
        for col, otra in enumerate(m.ids):
            valor = m.de(una, otra)
            if fila == col:
                fondo, texto, letra = "#f8fafc", "", SUAVE
            elif valor is None:
                fondo, texto, letra = REJILLA, "—", SUAVE
            else:
                fondo = _mezcla(
                    JUNTAS if valor >= 0 else AL_REVES, 0.08 + 0.92 * abs(valor)
                )
                texto = f"{valor:+.2f}".replace(".", ",")
                # En las casillas oscuras el negro no se lee.
                letra = FONDO if abs(valor) >= 0.55 else TEXTO
            ax.add_patch(
                Rectangle((col, fila), 0.94, 0.94, facecolor=fondo, edgecolor="none")
            )
            ax.text(
                col + 0.47,
                fila + 0.5,
                texto,
                ha="center",
                va="center",
                fontsize=9 if n > 6 else 10.5,
                color=letra,
                weight="bold",
            )
    ax.set_xlim(-0.03, n)
    ax.set_ylim(n, -0.03)
    ax.set_xticks([i + 0.47 for i in range(n)], nombres)
    ax.set_yticks([i + 0.47 for i in range(n)], nombres)
    ax.xaxis.tick_top()
    ax.tick_params(length=0, labelsize=9, colors=TEXTO)
    for borde in ax.spines.values():
        borde.set_visible(False)

    fig.text(
        0.3 / ancho,
        0.22 / alto,
        "+1 se mueven igual · 0 nada que ver · −1 una sube si la otra baja",
        fontsize=8.5,
        color=SUAVE,
    )
    salida = io.BytesIO()
    fig.savefig(salida, format="png", facecolor=FONDO)
    return salida.getvalue()


INICIALES = "EFMAMJJASOND"


def dibujar_tarjeta_anual(t: TarjetaAnual) -> bytes:
    """Como /tarjeta, pero del año entero. Tampoco lleva ni una cifra en dinero."""
    try:
        import numpy as np
        from matplotlib.figure import Figure
    except ImportError as e:
        raise GraficaError(
            "Falta matplotlib. Ejecuta: pip install -r requirements.txt"
        ) from e

    if t.total is not None:
        grande, debajo = _pct_tarjeta(t.total), "mi cartera en el año"
        if t.desde:
            debajo = f"mi cartera desde el {t.desde:%d/%m}"
        bueno = t.total >= 0
    else:
        grande, debajo = f"{t.verdes} de {t.juzgadas}", "compras van ganando"
        bueno = t.verdes * 2 >= t.juzgadas
    color = VERDE_NOCHE if bueno else ROJO_NOCHE

    fig = Figure(figsize=(7.2, 7.2), dpi=150, facecolor=NOCHE)
    _brillo(fig, np, color)

    fig.text(
        0.08, 0.92, f"MI {t.año} EN CRIPTO", fontsize=11, weight="bold", color=APAGADO
    )
    if t.hasta:
        fig.text(
            0.92,
            0.92,
            f"hasta el {t.hasta:%d/%m}",
            fontsize=11,
            color=APAGADO,
            ha="right",
        )
    fig.text(0.075, 0.76, grande, fontsize=62, weight="bold", color=color)
    fig.text(0.08, 0.70, debajo, fontsize=13, color=CLARO)

    if t.meses:
        _meses_tarjeta(fig, t.meses)

    datos = []
    if t.mejor:
        coin_id, cambio = t.mejor
        titulo = "LA QUE MÁS SUBIÓ" if cambio > 0 else "LA QUE MEJOR FUE"
        datos.append((titulo, f"{_corto(coin_id)} {_pct_tarjeta(cambio)}"))
    if t.mejor_mes:
        mes, cambio = t.mejor_mes
        datos.append(("MEJOR MES", f"{MESES[mes - 1].title()} {_pct_tarjeta(cambio)}"))
    if t.compras or t.ventas:
        compras = f"{t.compras} compra{'s' if t.compras != 1 else ''}"
        ventas = f"{t.ventas} venta{'s' if t.ventas != 1 else ''}"
        datos.append(("MOVIMIENTOS", f"{compras} · {ventas}"))
    if t.mejor_compra:
        coin_id, cambio = t.mejor_compra
        datos.append(("MEJOR COMPRA", f"{_corto(coin_id)} {_pct_tarjeta(cambio)}"))
    # Sin la gráfica de meses suben al hueco que deja, si no queda un vacío.
    arriba = 0.25 if t.meses else 0.52
    for i, (titulo, valor) in enumerate(datos[:4]):
        x = 0.08 + (i % 2) * 0.44
        y = arriba - (i // 2) * 0.10
        fig.text(x, y + 0.035, titulo, fontsize=8.5, weight="bold", color=APAGADO)
        fig.text(x, y, valor, fontsize=15, weight="bold", color=CLARO)

    fig.text(
        0.5,
        0.04,
        "Solo porcentajes, sin cifras · CryptoPriceTracker",
        fontsize=8,
        color=APAGADO,
        ha="center",
        alpha=0.7,
    )
    salida = io.BytesIO()
    fig.savefig(salida, format="png", facecolor=NOCHE)
    return salida.getvalue()


def _meses_tarjeta(fig, meses: dict[int, float]) -> None:
    ax = fig.add_axes((0.08, 0.40, 0.84, 0.22))
    ax.set_facecolor("none")
    tope = max(abs(v) for v in meses.values()) or 1
    for i in range(12):
        cambio = meses.get(i + 1)
        if cambio is None:
            # Sin precios ese mes: una raya, para que no parezca un 0%.
            ax.bar(
                i,
                tope * 0.02,
                bottom=-tope * 0.01,
                width=0.62,
                color=APAGADO,
                alpha=0.3,
            )
            continue
        color = VERDE_NOCHE if cambio >= 0 else ROJO_NOCHE
        ax.bar(i, cambio, width=0.62, color=color, lw=0)
    ax.axhline(0, color=APAGADO, lw=0.8, alpha=0.5)
    ax.set_ylim(-tope * 1.15, tope * 1.15)
    ax.set_xlim(-0.6, 11.6)
    ax.set_xticks(range(12), list(INICIALES))
    ax.tick_params(axis="x", colors=APAGADO, length=0, labelsize=9)
    ax.set_yticks([])
    for borde in ax.spines.values():
        borde.set_visible(False)


def _brillo(fig, np, color: str) -> None:
    """Una mancha grande y suave del color del resultado, arriba a la derecha."""
    r, g, b = (int(color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    fondo = [int(NOCHE[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    y, x = np.mgrid[0:1:300j, 0:1:300j]
    fuerza = np.exp(-((x - 0.85) ** 2 + (y - 0.1) ** 2) / 0.12) * 0.22
    imagen = np.empty((300, 300, 3))
    for canal, (de, a) in enumerate(zip(fondo, (r, g, b), strict=True)):
        imagen[..., canal] = de + (a - de) * fuerza
    ax = fig.add_axes((0, 0, 1, 1), zorder=-1)
    ax.imshow(imagen, extent=(0, 1, 0, 1), aspect="auto", interpolation="bicubic")
    ax.axis("off")


def _linea_tarjeta(fig, linea: list[float]) -> None:
    color = VERDE_NOCHE if linea[-1] >= 0 else ROJO_NOCHE
    ax = fig.add_axes((0.08, 0.34, 0.84, 0.25))
    ax.set_facecolor("none")
    x = range(len(linea))
    suelo = min(linea)
    ax.plot(x, linea, color=color, lw=2.4, solid_capstyle="round")
    ax.fill_between(x, linea, suelo, color=color, alpha=0.12, lw=0)
    # El 0 es donde empezó el tramo: por encima, ganando.
    ax.axhline(0, color=APAGADO, lw=0.8, ls=(0, (2, 3)), alpha=0.5)
    ax.plot(len(linea) - 1, linea[-1], "o", color=color, ms=7)
    ax.set_xlim(0, len(linea) - 1)
    ax.axis("off")


def _reparto_tarjeta(fig, trozos: list[Trozo]) -> None:
    fig.text(0.08, 0.255, "REPARTO", fontsize=9, weight="bold", color=APAGADO)
    ax = fig.add_axes((0.08, 0.2, 0.84, 0.035))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 1)
    ax.axis("off")
    izquierda = 0.0
    colores = []
    for trozo in trozos:
        color = GRIS if trozo.color is None else PALETA[trozo.color % len(PALETA)]
        colores.append(color)
        # Una raya del fondo entre trozos, para que no se peguen.
        ax.barh(0.5, trozo.peso, left=izquierda, height=1, color=color, lw=0)
        ax.barh(0.5, 0.6, left=izquierda + trozo.peso - 0.3, height=1, color=NOCHE)
        izquierda += trozo.peso

    # Como mucho cuatro en la leyenda: con más ya no caben y se lee mal.
    for i, (trozo, color) in enumerate(zip(trozos[:4], colores, strict=False)):
        x = 0.08 + i * 0.21
        nombre = "Otras" if trozo.coin_id == OTRAS else trozo.coin_id.title()
        fig.text(x, 0.145, "●", fontsize=12, color=color)
        fig.text(
            x + 0.03,
            0.147,
            f"{nombre[:10]} {trozo.peso:.0f}%",
            fontsize=10,
            color=CLARO,
        )


# Lo cerca de un borde (de 0 a 1) a partir de lo cual la etiqueta va hacia dentro.
BORDE = 0.12


def _alineacion(donde: float) -> str:
    """Centrada sobre el punto, salvo en los bordes: a la izquierda pisaba los
    números del eje y a la derecha se salía de la gráfica."""
    if donde < BORDE:
        return "left"
    if donde > 1 - BORDE:
        return "right"
    return "center"


def _corto(coin_id: str) -> str:
    """BTC, AVAX... A la derecha de la gráfica no cabe «Polygon Ecosystem Token»."""
    nombre = de_id(coin_id) or coin_id.replace("-", " ").title()
    return nombre if len(nombre) <= 12 else nombre[:11] + "…"


def _pct_eje(valor: float, decimales: int) -> str:
    texto = f"{valor:+.{decimales}f}".replace(".", ",")
    # Sin esto el de en medio sale como «+0%» o «-0%».
    if float(texto.replace(",", ".")) == 0:
        return "0%"
    return texto + "%"


def _en_el_tramo(horas: float) -> str:
    """'en los últimos 30 días', 'en las últimas 24 h', 'en la última hora'."""
    tramo = nombre_periodo(horas)
    if tramo.startswith("última "):
        return f"en la {tramo}"
    return f"en {'las' if tramo.startswith('últimas') else 'los'} {tramo}"


def _pct_tarjeta(valor: float) -> str:
    return f"{valor:+.1f}%".replace(".", ",")


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
