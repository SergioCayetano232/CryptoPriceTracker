"""/ahr999: si con bitcoin toca comprar fuerte, hacer DCA o esperar."""

import math
from dataclasses import dataclass
from datetime import date, datetime, timezone

GENESIS = date(2009, 1, 3)
DIAS = 200
# La curva de crecimiento tal cual la publicó ahr999 en 2019. No la reajusto:
# así la cifra cuadra con la que dan las webs que lo siguen.
PENDIENTE = 5.84
CORTE = -17.01

COMPRAR = 0.45
ESPERAR = 1.2
ZONAS = (
    (COMPRAR, "🟢", "Zona de comprar fuerte: así estaba en los fondos"),
    (ESPERAR, "🔵", "Zona de DCA: comprar poco a poco"),
    (float("inf"), "🟠", "Zona de esperar: caro para lo que suele"),
)


@dataclass(frozen=True)
class Dia:
    cuando: date
    precio: float
    coste: float  # la media geométrica de 200 días: lo que costó comprar a diario
    crecimiento: float  # lo que debería valer según la curva

    @property
    def indice(self) -> float:
        return (self.precio / self.coste) * (self.precio / self.crecimiento)

    def precio_para(self, indice: float) -> float:
        """El precio al que el índice de hoy daría eso, sin mover la media."""
        return math.sqrt(indice * self.coste * self.crecimiento)


@dataclass(frozen=True)
class Ahr999:
    dias: list[Dia]  # los que ya tienen 200 detrás, del más viejo a hoy

    @property
    def hoy(self) -> Dia:
        return self.dias[-1]

    @property
    def mas_bajos(self) -> int:
        """Los días que estuvo más bajo que hoy."""
        return sum(d.indice < self.hoy.indice for d in self.dias)

    @property
    def por_debajo(self) -> float:
        return 100 * self.mas_bajos / len(self.dias)

    @property
    def minimo(self) -> Dia:
        return min(self.dias, key=lambda d: d.indice)

    @property
    def zona(self) -> tuple[str, str]:
        return next((e, t) for tope, e, t in ZONAS if self.hoy.indice < tope)

    def ultima_vez(self, debajo_de: float) -> Dia | None:
        """El último día, sin contar los de esta racha, que estuvo por debajo."""
        i = len(self.dias) - 1
        while i >= 0 and self.dias[i].indice < debajo_de:
            i -= 1
        return next(
            (d for d in reversed(self.dias[: i + 1]) if d.indice < debajo_de), None
        )


def crecimiento(cuando: date) -> float:
    edad = max((cuando - GENESIS).days, 1)
    return 10 ** (PENDIENTE * math.log10(edad) + CORTE)


def calcular(velas) -> Ahr999 | None:
    """Con las velas diarias de /mayer. None si no hay 200 días."""
    cierres: dict[date, float] = {}
    for v in velas if isinstance(velas, list) else []:
        try:
            dia = datetime.fromtimestamp(int(v[0]) / 1000, timezone.utc).date()
            precio = float(v[4])
        except (TypeError, ValueError, IndexError, OverflowError, OSError):
            continue
        if precio > 0 and math.isfinite(precio):
            cierres[dia] = precio
    fechas = sorted(cierres)
    logs = [math.log(cierres[f]) for f in fechas]
    if len(logs) < DIAS:
        return None

    dias = []
    suma = sum(logs[:DIAS])
    for i in range(DIAS - 1, len(logs)):
        if i >= DIAS:
            suma += logs[i] - logs[i - DIAS]
        cuando = fechas[i]
        coste = math.exp(suma / DIAS)
        dias.append(Dia(cuando, cierres[cuando], coste, crecimiento(cuando)))
    return Ahr999(dias)
