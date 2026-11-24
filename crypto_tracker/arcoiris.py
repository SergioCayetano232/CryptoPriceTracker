"""/arcoiris: en qué franja está bitcoin respecto a su curva de largo plazo."""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

GENESIS = datetime(2009, 1, 3, tzinfo=timezone.utc)

# De abajo arriba. El color va en grafica.py.
FRANJAS = (
    "Saldo: casi regalado",
    "Compra",
    "Acumula",
    "Todavía barato",
    "HODL",
    "¿Es una burbuja?",
    "FOMO",
    "Vende, en serio",
    "Burbuja máxima",
)

# Con menos de dos años la curva sale con cualquier pendiente.
MINIMO = 730


@dataclass(frozen=True)
class Arcoiris:
    dias: list[tuple[datetime, float]]  # (día, precio), del más viejo a hoy
    a: float  # log10(precio) = a + b * log10(días desde el génesis)
    b: float
    bordes: list[float]  # 10 bordes de las franjas, en log10 sobre la curva

    def curva(self, cuando: datetime) -> float:
        """El precio de la curva ese día."""
        return 10 ** (self.a + self.b * math.log10(_dias(cuando)))

    def precio_borde(self, cuando: datetime, borde: int) -> float:
        return self.curva(cuando) * 10 ** self.bordes[borde]

    @property
    def hoy(self) -> tuple[datetime, float]:
        return self.dias[-1]

    @property
    def sobre_curva(self) -> float:
        """% que está por encima (o por debajo) de la curva hoy."""
        cuando, precio = self.hoy
        return (precio / self.curva(cuando) - 1) * 100

    @property
    def franja(self) -> int:
        """De 0 (la de abajo) a 8."""
        cuando, precio = self.hoy
        resto = math.log10(precio / self.curva(cuando))
        dentro = [i for i in range(len(FRANJAS)) if resto >= self.bordes[i]]
        return min(max(dentro, default=0), len(FRANJAS) - 1)


def _dias(cuando: datetime) -> float:
    return max((cuando - GENESIS) / timedelta(days=1), 1)


def calcular(velas) -> Arcoiris | None:
    """Ajusta la curva con mínimos cuadrados en escala logarítmica.

    velas son las diarias de Binance que pide /mayer, desde 2017.
    """
    cierres = {}
    for v in velas if isinstance(velas, list) else []:
        try:
            cuando = datetime.fromtimestamp(int(v[0]) / 1000, timezone.utc)
            precio = float(v[4])
        except (TypeError, ValueError, IndexError, OverflowError, OSError):
            continue
        if precio > 0 and math.isfinite(precio) and cuando > GENESIS:
            cierres[cuando] = precio
    dias = sorted(cierres.items())
    if len(dias) < MINIMO:
        return None

    xs = [math.log10(_dias(c)) for c, _ in dias]
    ys = [math.log10(p) for _, p in dias]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    varianza = sum((x - mx) ** 2 for x in xs)
    if not varianza:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / varianza
    a = my - b * mx

    restos = [y - (a + b * x) for x, y in zip(xs, ys, strict=True)]
    # Las franjas, a partes iguales entre lo más bajo y lo más alto que ha estado.
    bajo, alto = min(restos), max(restos)
    paso = (alto - bajo) / len(FRANJAS)
    bordes = [bajo + i * paso for i in range(len(FRANJAS) + 1)]
    return Arcoiris(dias, a, b, bordes)
