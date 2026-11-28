"""/paciencia: comprar un día cualquiera y aguantar, ¿cuántas veces salía bien?"""

import math
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

PLAZOS = (
    (30, "1 mes"),
    (182, "6 meses"),
    (365, "1 año"),
    (730, "2 años"),
    (1095, "3 años"),
    (1461, "4 años"),
)
# Con menos compras que estas el % no dice nada.
MINIMO = 30

EJEMPLO = "/paciencia btc"


@dataclass(frozen=True)
class Compra:
    cuando: date
    precio: float
    despues: float

    @property
    def cambio(self) -> float:
        return (self.despues / self.precio - 1) * 100


@dataclass(frozen=True)
class Plazo:
    dias: int
    nombre: str
    compras: list[Compra]  # una por día, de la más vieja a la última posible

    @property
    def ganaba(self) -> float:
        """% de las compras que estaban en positivo al acabar el plazo."""
        return 100 * sum(c.cambio > 0 for c in self.compras) / len(self.compras)

    @property
    def mediana(self) -> float:
        return statistics.median(c.cambio for c in self.compras)

    @property
    def peor(self) -> Compra:
        return min(self.compras, key=lambda c: c.cambio)


@dataclass(frozen=True)
class Paciencia:
    plazos: list[Plazo]  # los que tienen bastantes compras, del más corto al más largo
    hoy: date
    precio: float  # el de hoy
    # (plazo, lo que valía hace ese tiempo) para el más largo
    hace: tuple[Plazo, Compra] | None


def calcular(velas) -> Paciencia | None:
    """Con las velas diarias de /mayer. None si no llega ni para un mes."""
    cierres: dict[date, float] = {}
    for v in velas if isinstance(velas, list) else []:
        try:
            dia = datetime.fromtimestamp(int(v[0]) / 1000, timezone.utc).date()
            precio = float(v[4])
        except (TypeError, ValueError, IndexError, OverflowError, OSError):
            continue
        if precio > 0 and math.isfinite(precio):
            cierres[dia] = precio
    if not cierres:
        return None
    hoy = max(cierres)

    plazos = []
    for dias, nombre in PLAZOS:
        salto = timedelta(days=dias)
        compras = [
            Compra(dia, precio, cierres[dia + salto])
            for dia, precio in sorted(cierres.items())
            if dia + salto in cierres
        ]
        if len(compras) >= MINIMO:
            plazos.append(Plazo(dias, nombre, compras))
    if not plazos:
        return None

    largo = plazos[-1]
    inicio = hoy - timedelta(days=largo.dias)
    hace = None
    if inicio in cierres:
        hace = (largo, Compra(inicio, cierres[inicio], cierres[hoy]))
    return Paciencia(plazos, hoy, cierres[hoy], hace)
