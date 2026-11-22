"""Dibuja el PDF de /informe: una hoja de resumen y la tabla de ventas detrás."""

import io
from datetime import date

from .alerts import SIMBOLOS
from .grafica import FONDO, REJILLA, ROJO, SUAVE, TEXTO, VERDE, GraficaError, _eje
from .informe import Informe, hojas
from .mes import MESES
from .movimientos import texto_cantidad
from .renta import Venta

# Un A4 de pie, en pulgadas.
ANCHO, ALTO = 8.27, 11.69
IZQ, DER = 0.08, 0.92

# Más criptos que estas no caben en su gráfica; el resto va junto.
MAX_CRIPTOS = 8

AVISO = (
    "Orientativo, no es asesoramiento fiscal. Calculado con FIFO, como pide Hacienda."
)


def dibujar(informe: Informe, currency: str, hoy: date) -> bytes:
    """El PDF entero. Lanza GraficaError si falta matplotlib."""
    try:
        from matplotlib.backends.backend_pdf import PdfPages
    except ImportError as e:
        raise GraficaError(
            "Falta matplotlib. Ejecuta: pip install -r requirements.txt"
        ) from e

    salida = io.BytesIO()
    titulo = f"Informe fiscal {informe.año}"
    with PdfPages(salida, metadata={"Title": titulo, "Creator": None}) as pdf:
        for hoja in paginas(informe, currency, hoy):
            pdf.savefig(hoja, facecolor=FONDO)
    return salida.getvalue()


def paginas(informe: Informe, currency: str, hoy: date) -> list:
    """Las hojas, cada una en su figura. Aparte, para poder mirarlas en PNG."""
    from matplotlib.figure import Figure

    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    trozos = hojas(informe.ventas)
    total = 1 + len(trozos)

    def nueva() -> Figure:
        return Figure(figsize=(ANCHO, ALTO), facecolor=FONDO)

    lista = [_resumen(nueva(), informe, simbolo, currency, hoy)]
    for i, trozo in enumerate(trozos):
        ultima = i == len(trozos) - 1
        lista.append(_tabla(nueva(), informe, trozo, simbolo, ultima))
    for n, fig in enumerate(lista, start=1):
        _pie(fig, n, total)
    return lista


def _y(pulgadas: float) -> float:
    """De pulgadas desde arriba a la fracción de la hoja que usa matplotlib."""
    return 1 - pulgadas / ALTO


def _dinero(valor: float, simbolo: str) -> str:
    # Siempre con dos decimales, como en la Renta: _num le pondría seis a un
    # céntimo de cardano.
    cifra = f"{abs(valor):,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    # Lo que se queda en cero al redondear no lleva signo.
    signo = "-" if valor < 0 and cifra != "0,00" else ""
    return f"{signo}{simbolo}{cifra}"


def _del_eje(valor: float, simbolo: str) -> str:
    if not valor:
        return f"{simbolo}0"
    return ("-" if valor < 0 else "") + simbolo + _eje(abs(valor))


def _con_signo(valor: float, simbolo: str) -> str:
    texto = _dinero(valor, simbolo)
    return texto if valor <= 0 or texto == f"{simbolo}0,00" else "+" + texto


def _color(valor: float) -> str:
    return VERDE if valor >= 0 else ROJO


def _nombre(coin_id: str) -> str:
    return coin_id.replace("-", " ").title()


def _pie(fig, pagina: int, total: int) -> None:
    fig.text(IZQ, _y(11.15), AVISO, fontsize=7, color=SUAVE, va="center")
    fig.text(
        DER,
        _y(11.15),
        f"{pagina} de {total}",
        fontsize=7,
        color=SUAVE,
        va="center",
        ha="right",
    )


def _raya(fig, pulgadas: float) -> None:
    from matplotlib.lines import Line2D

    fig.add_artist(
        Line2D(
            [IZQ, DER],
            [_y(pulgadas)] * 2,
            color=REJILLA,
            linewidth=0.8,
            transform=fig.transFigure,
        )
    )


def _resumen(fig, informe: Informe, simbolo: str, currency: str, hoy: date):
    fig.text(
        IZQ,
        _y(0.95),
        f"Informe fiscal {informe.año}",
        fontsize=22,
        weight="bold",
        color=TEXTO,
    )
    fig.text(
        IZQ,
        _y(1.25),
        "Criptomonedas · ganancias y pérdidas por lo vendido en el año",
        fontsize=10,
        color=SUAVE,
    )
    fig.text(
        DER,
        _y(0.95),
        f"Hecho el {hoy:%d/%m/%Y}",
        fontsize=9,
        color=SUAVE,
        ha="right",
    )
    _raya(fig, 1.5)

    ganancia = informe.impuestos.ganancia
    cuantas = len(informe.ventas)
    cifras = [
        ("Ventas", str(cuantas), TEXTO),
        ("Valor de transmisión", _dinero(informe.transmision, simbolo), TEXTO),
        ("Valor de adquisición", _dinero(informe.adquisicion, simbolo), TEXTO),
        (
            "Ganancia" if ganancia >= 0 else "Pérdida",
            _con_signo(ganancia, simbolo),
            _color(ganancia),
        ),
    ]
    hueco = (DER - IZQ) / len(cifras)
    for i, (rotulo, valor, color) in enumerate(cifras):
        x = IZQ + hueco * i
        fig.text(x, _y(1.95), rotulo, fontsize=8.5, color=SUAVE)
        fig.text(x, _y(2.3), valor, fontsize=14, weight="bold", color=color)

    y = _hacienda(fig, informe, simbolo, 2.95)
    y = _otros(fig, informe, simbolo, currency, y + 0.35)

    if informe.contadas:
        y = _barras_mes(fig, informe, simbolo, y + 0.3)
        _barras_cripto(fig, informe, simbolo, y + 0.45)
    return fig


def _hacienda(fig, informe: Informe, simbolo: str, y: float) -> float:
    """El bloque de la cuota. Devuelve por dónde va, en pulgadas desde arriba."""
    i = informe.impuestos
    fig.text(
        IZQ, _y(y), "Lo que le tocaría a Hacienda", fontsize=12, weight="bold",
        color=TEXTO,
    )  # fmt: skip
    y += 0.32
    if not informe.ventas:
        fig.text(IZQ, _y(y), "No has vendido nada este año.", fontsize=10, color=TEXTO)
        return y
    if not informe.contadas:
        fig.text(
            IZQ,
            _y(y),
            "A tus ventas les falta el precio o lo que costaron: no se puede calcular.",
            fontsize=10,
            color=TEXTO,
        )
        return y
    if i.ganancia <= 0:
        fig.text(
            IZQ,
            _y(y),
            "Nada. Y esa pérdida la puedes restar de lo que ganes los próximos 4 años.",
            fontsize=10,
            color=TEXTO,
        )
        return y

    for tipo, base, cuota in i.tramos:
        fig.text(IZQ, _y(y), f"Al {tipo}%", fontsize=10, color=TEXTO)
        fig.text(0.42, _y(y), _dinero(base, simbolo), fontsize=10, color=SUAVE,
                 ha="right")  # fmt: skip
        fig.text(0.62, _y(y), _dinero(cuota, simbolo), fontsize=10, color=TEXTO,
                 ha="right")  # fmt: skip
        y += 0.24
    fig.text(IZQ, _y(y + 0.05), "Total", fontsize=10.5, weight="bold", color=TEXTO)
    fig.text(
        0.62,
        _y(y + 0.05),
        _dinero(i.total, simbolo),
        fontsize=10.5,
        weight="bold",
        color=TEXTO,
        ha="right",
    )
    media = f"{i.tipo_medio:.2f}".replace(".", ",")
    fig.text(0.64, _y(y + 0.05), f"{media}% de media", fontsize=9, color=SUAVE)
    return y + 0.05


def _otros(fig, informe: Informe, simbolo: str, currency: str, y: float) -> float:
    """Lo que no es la cuota: recompensas, comisiones y los avisos."""
    lineas = []
    if informe.recompensas:
        lineas.append(
            f"Recompensas recibidas (staking, airdrops): "
            f"{_dinero(informe.recompensas, simbolo)}. También tributan y no van "
            "sumadas arriba."
        )
    c = informe.comisiones
    if c.con:
        veces = "1 operación" if c.con == 1 else f"{c.con} operaciones"
        lineas.append(
            f"Comisiones pagadas: {_dinero(c.total, simbolo)} en {veces}. Ya van "
            "dentro de los valores de arriba."
        )
    fuera = len(informe.ventas) - len(informe.contadas)
    if fuera:
        cuantas = "1 venta" if fuera == 1 else f"{fuera} ventas"
        lineas.append(
            f"Fuera de las cuentas: {cuantas} sin precio o sin lo que costaron."
        )
    if currency.lower() != "eur":
        lineas.append(
            f"Ojo: todo va en {currency.upper()}, y Hacienda lo quiere en euros."
        )
    if not lineas:
        return y - 0.35
    _raya(fig, y - 0.1)
    y += 0.15
    for linea in lineas:
        fig.text(IZQ, _y(y), linea, fontsize=9, color=TEXTO)
        y += 0.22
    return y - 0.22


def _limpiar(ax) -> None:
    ax.set_facecolor(FONDO)
    for lado in ("top", "right", "left", "bottom"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(length=0, labelsize=8, labelcolor=SUAVE)


def _barras_mes(fig, informe: Informe, simbolo: str, y: float) -> float:
    from matplotlib.ticker import FuncFormatter

    fig.text(IZQ, _y(y), "Ganancia de cada mes", fontsize=12, weight="bold",
             color=TEXTO)  # fmt: skip
    alto = 2.0
    ax = fig.add_axes((IZQ + 0.06, _y(y + 0.2 + alto), DER - IZQ - 0.06, alto / ALTO))
    _limpiar(ax)
    valores = informe.por_mes
    ax.bar(range(12), valores, color=[_color(v) for v in valores], width=0.62)
    ax.axhline(0, color=SUAVE, linewidth=0.8)
    ax.set_xticks(range(12), [m[:3] for m in MESES])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _del_eje(v, simbolo)))
    ax.yaxis.grid(True, color=REJILLA, linewidth=0.6)
    ax.set_axisbelow(True)
    # Aire para que el cero no quede pegado al borde si todo va hacia un lado.
    tope = max(abs(v) for v in valores) or 1
    ax.set_ylim(min(0, min(valores)) - tope * 0.08, max(0, max(valores)) + tope * 0.08)
    return y + 0.2 + alto


def _barras_cripto(fig, informe: Informe, simbolo: str, y: float) -> None:
    lista = list(informe.por_cripto)
    if len(lista) > MAX_CRIPTOS:
        resto = sum(g for _, g in lista[MAX_CRIPTOS - 1 :])
        lista = [*lista[: MAX_CRIPTOS - 1], ("Las demás", resto)]

    fig.text(IZQ, _y(y), "Por cripto", fontsize=12, weight="bold", color=TEXTO)
    fila = 0.27
    tope = max(abs(g) for _, g in lista) or 1
    # La barra sale del centro: a la derecha lo ganado y a la izquierda lo perdido.
    centro, medio = 0.52, 0.2
    from matplotlib.patches import Rectangle

    for i, (coin_id, ganancia) in enumerate(lista):
        linea = _y(y + 0.35 + fila * i)
        fig.text(IZQ, linea, _nombre(coin_id), fontsize=9.5, color=TEXTO, va="center")
        largo = medio * abs(ganancia) / tope
        fig.patches.append(
            Rectangle(
                (centro if ganancia >= 0 else centro - largo, linea - 0.07 / ALTO),
                largo,
                0.14 / ALTO,
                facecolor=_color(ganancia),
                transform=fig.transFigure,
                figure=fig,
            )
        )
        fig.text(
            DER,
            linea,
            _con_signo(ganancia, simbolo),
            fontsize=9.5,
            color=_color(ganancia),
            va="center",
            ha="right",
        )


COLUMNAS = (
    ("Fecha", IZQ, "left"),
    ("Cripto", 0.2, "left"),
    ("Cantidad", 0.5, "right"),
    ("Transmisión", 0.64, "right"),
    ("Adquisición", 0.78, "right"),
    ("Ganancia", DER, "right"),
)


def _fila(fig, y: float, celdas: list[tuple[str, str]], negrita: bool = False) -> None:
    for (_, x, lado), (texto, color) in zip(COLUMNAS, celdas, strict=True):
        fig.text(
            x,
            _y(y),
            texto,
            fontsize=8.5,
            color=color,
            ha=lado,
            va="center",
            weight="bold" if negrita else "normal",
        )


def _celdas(v: Venta, simbolo: str) -> list[tuple[str, str]]:
    def opcional(valor: float | None) -> str:
        return "—" if valor is None else _dinero(valor, simbolo)

    ganancia = ("—", SUAVE)
    if v.ganancia is not None:
        texto = _con_signo(v.ganancia, simbolo)
        # Un céntimo perdido que se queda en cero no es una pérdida que marcar.
        cero = texto == f"{simbolo}0,00"
        ganancia = (texto, TEXTO if cero else _color(v.ganancia))
    return [
        (f"{v.cuando:%d/%m/%Y}", TEXTO),
        (_nombre(v.coin_id), TEXTO),
        (texto_cantidad(v.cantidad), TEXTO),
        (opcional(v.transmision), TEXTO),
        (opcional(v.adquisicion), TEXTO),
        ganancia,
    ]


def _tabla(fig, informe: Informe, ventas: list[Venta], simbolo: str, ultima: bool):
    fig.text(
        IZQ,
        _y(0.95),
        f"Ventas de {informe.año}",
        fontsize=16,
        weight="bold",
        color=TEXTO,
    )
    y = 1.5
    _fila(fig, y, [(rotulo, SUAVE) for rotulo, _, _ in COLUMNAS], negrita=True)
    _raya(fig, y + 0.16)
    paso = 0.28
    y += 0.4
    for v in ventas:
        _fila(fig, y, _celdas(v, simbolo))
        y += paso

    if ultima and informe.contadas:
        _raya(fig, y - 0.1)
        ganancia = informe.impuestos.ganancia
        total = [
            ("Total", TEXTO),
            ("", TEXTO),
            ("", TEXTO),
            (_dinero(informe.transmision, simbolo), TEXTO),
            (_dinero(informe.adquisicion, simbolo), TEXTO),
            (_con_signo(ganancia, simbolo), _color(ganancia)),
        ]
        _fila(fig, y + 0.12, total, negrita=True)
    return fig
