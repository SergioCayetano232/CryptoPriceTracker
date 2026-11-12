"""/diames: qué día del mes suele salir más barato comprar."""

from dataclasses import dataclass
from datetime import date

from .periodo import PeriodoError, es_tramo, leer
from .simbolos import a_id

# Con 90 días serían tres veces cada día: casi azar. Un año ya dice algo.
POR_DEFECTO = 365 * 24

EJEMPLO = "/diames bitcoin 365d"

# Cada día contra la media de los 15 de antes y los 15 de después. Contra la de
# su mes no vale: si el precio sube, el día 1 saldría siempre el más barato.
VENTANA = 15
# Por debajo, que un día salga barato puede ser un solo mes con un desplome.
POCOS_MESES = 6

TERCIOS = [
    ("Del 1 al 10", 1, 10),
    ("Del 11 al 20", 11, 20),
    ("Del 21 al final", 21, 31),
]


@dataclass(frozen=True)
class DiaMes:
    dia: int
    media: float  # cuánto está por encima o por debajo de la media de su mes, en %
    veces: int


@dataclass(frozen=True)
class DiasMes:
    dias: list[DiaMes]  # del 1 al 31, solo los que tienen dato
    meses: int
    desde: date

    @property
    def barato(self) -> DiaMes:
        return min(self.dias, key=lambda d: d.media)

    @property
    def caro(self) -> DiaMes:
        return max(self.dias, key=lambda d: d.media)

    def de(self, dia: int) -> DiaMes | None:
        return next((d for d in self.dias if d.dia == dia), None)

    def tercios(self) -> list[tuple[str, float]]:
        """La media de cada tercio, con cada día pesando las veces que salió."""
        lista = []
        for nombre, desde, hasta in TERCIOS:
            dentro = [d for d in self.dias if desde <= d.dia <= hasta]
            veces = sum(d.veces for d in dentro)
            if veces:
                lista.append((nombre, sum(d.media * d.veces for d in dentro) / veces))
        return lista


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 180d' -> ('bitcoin', 4320). Sin tramo, un año; sin cripto, ''."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if len(partes) > 1:
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")
    return (a_id(partes[0]) if partes else ""), horas


def calcular(dias: list[tuple[date, float]]) -> DiasMes | None:
    """dias es el último precio de cada día (sale de por_dias). None si no hay
    ni un día con los VENTANA de antes y de después guardados."""
    seguidos = [(d, p) for d, p in dias if p > 0]
    diferencias: dict[int, list[float]] = {}
    for i in range(VENTANA, len(seguidos) - VENTANA):
        trozo = seguidos[i - VENTANA : i + VENTANA + 1]
        # Con huecos, la media sería de otras fechas.
        if (trozo[-1][0] - trozo[0][0]).days != 2 * VENTANA:
            continue
        dia, precio = seguidos[i]
        media = sum(p for _, p in trozo) / len(trozo)
        diferencias.setdefault(dia.day, []).append((precio / media - 1) * 100)

    if not diferencias:
        return None
    contados = [
        d for i, (d, _) in enumerate(seguidos) if VENTANA <= i < len(seguidos) - VENTANA
    ]
    return DiasMes(
        [DiaMes(d, sum(c) / len(c), len(c)) for d, c in sorted(diferencias.items())],
        # Del 16 de enero al 15 de abril son tres meses, aunque toque cuatro.
        max(1, round(len(contados) / 30.4)),
        contados[0],
    )
