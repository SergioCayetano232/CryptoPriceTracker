"""/picycle: la media de 111 días contra el doble de la de 350, que marca techos."""

from dataclasses import dataclass
from datetime import date, datetime, timezone

RAPIDA = 111
LENTA = 350
# Lo que tarda en llegar el máximo tras el cruce. En 2021 fueron dos días.
TRAS_CRUCE = 30

# La rápida entre la lenta por dos: en 1 se cruzan.
ZONAS = (
    (0.7, "🧊", "Lejos del techo: ni rastro de cruce"),
    (0.9, "🟡", "Acercándose"),
    (1.0, "🔥", "A punto de cruzarse"),
    (float("inf"), "🚨", "Cruzadas: así marcó los techos de otros ciclos"),
)


@dataclass(frozen=True)
class Dia:
    cuando: date
    precio: float
    rapida: float
    lenta: float  # ya multiplicada por dos

    @property
    def ratio(self) -> float:
        return self.rapida / self.lenta


@dataclass(frozen=True)
class Cruce:
    dia: Dia
    maximo: Dia  # lo más alto en los TRAS_CRUCE días siguientes


@dataclass(frozen=True)
class PiCycle:
    dias: list[Dia]  # los que ya tienen 350 detrás, del más viejo a hoy

    @property
    def hoy(self) -> Dia:
        return self.dias[-1]

    @property
    def falta(self) -> float:
        """% que tiene que subir la rápida para tocar a la lenta."""
        return (1 / self.hoy.ratio - 1) * 100

    @property
    def cruces(self) -> list[Cruce]:
        """Las veces que la rápida pasó por encima: la señal de techo."""
        lista = []
        for i in range(1, len(self.dias)):
            if self.dias[i - 1].ratio < 1 <= self.dias[i].ratio:
                despues = self.dias[i : i + TRAS_CRUCE + 1]
                lista.append(Cruce(self.dias[i], max(despues, key=lambda d: d.precio)))
        return lista

    @property
    def zona(self) -> tuple[str, str]:
        return next((e, t) for tope, e, t in ZONAS if self.hoy.ratio < tope)


def calcular(velas) -> PiCycle | None:
    """Con las velas diarias de /mayer. None si no hay 350 días."""
    cierres: dict[date, float] = {}
    for v in velas if isinstance(velas, list) else []:
        try:
            dia = datetime.fromtimestamp(int(v[0]) / 1000, timezone.utc).date()
            precio = float(v[4])
        except (TypeError, ValueError, IndexError, OverflowError, OSError):
            continue
        if precio > 0:
            cierres[dia] = precio
    fechas = sorted(cierres)
    precios = [cierres[f] for f in fechas]
    if len(precios) < LENTA:
        return None

    dias = []
    rapida = sum(precios[LENTA - RAPIDA : LENTA])
    lenta = sum(precios[:LENTA])
    for i in range(LENTA - 1, len(precios)):
        if i >= LENTA:
            rapida += precios[i] - precios[i - RAPIDA]
            lenta += precios[i] - precios[i - LENTA]
        dias.append(Dia(fechas[i], precios[i], rapida / RAPIDA, 2 * lenta / LENTA))
    return PiCycle(dias)
