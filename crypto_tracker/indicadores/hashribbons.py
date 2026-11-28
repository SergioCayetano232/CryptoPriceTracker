"""/hashribbons: si los mineros de bitcoin están capitulando."""

from dataclasses import dataclass
from datetime import date, datetime, timezone

from .comisionred import ComisionRedError, _get

URL = "https://mempool.space/api/v1/mining/hashrate/2y"
EXA = 1e18
CORTA = 30
LARGA = 60
# Con datos diarios las medias se cruzan y descruzan cada dos por tres. Junto
# lo que se separa menos de una semana y lo que dura menos, no lo cuento.
UNIR = 7
MINIMO = 7
# Tras acabar una capitulación, durante cuánto la doy por señal de compra.
SEÑAL = 30

HashRibbonsError = ComisionRedError


@dataclass(frozen=True)
class Dia:
    cuando: date
    potencia: float  # EH/s
    corta: float
    larga: float

    @property
    def capitula(self) -> bool:
        return self.corta < self.larga

    @property
    def distancia(self) -> float:
        """% de la media de 30 días sobre la de 60."""
        return (self.corta / self.larga - 1) * 100


@dataclass(frozen=True)
class Capitulacion:
    desde: date
    hasta: date | None  # None si sigue

    def dias(self, hoy: date) -> int:
        """Contando el primero y el último."""
        return ((self.hasta or hoy) - self.desde).days + 1


@dataclass(frozen=True)
class Ribbons:
    dias: list[Dia]  # los que ya tienen 60 detrás, del más viejo a hoy

    @property
    def hoy(self) -> Dia:
        return self.dias[-1]

    @property
    def capitulaciones(self) -> list[Capitulacion]:
        rachas: list[list[date]] = []
        for d in self.dias:
            if not d.capitula:
                continue
            if rachas and (d.cuando - rachas[-1][1]).days <= UNIR:
                rachas[-1][1] = d.cuando
            else:
                rachas.append([d.cuando, d.cuando])
        ultimo = self.hoy.cuando
        return [
            Capitulacion(desde, None if hasta == ultimo else hasta)
            for desde, hasta in rachas
            if (hasta - desde).days + 1 >= MINIMO or hasta == ultimo
        ]

    @property
    def estado(self) -> str:
        """'capitula', 'cruzando', 'señal' o 'sano'."""
        capitulaciones = self.capitulaciones
        ultima = capitulaciones[-1] if capitulaciones else None
        if ultima and ultima.hasta is None:
            if ultima.dias(self.hoy.cuando) >= MINIMO:
                return "capitula"
            return "cruzando"
        if ultima and (self.hoy.cuando - ultima.hasta).days <= SEÑAL:
            return "señal"
        return "sano"

    @property
    def pasadas(self) -> list[Capitulacion]:
        """Las que ya acabaron y duraron lo bastante para contar."""
        return [
            c
            for c in self.capitulaciones
            if c.hasta is not None and c.dias(c.hasta) >= MINIMO
        ]


def pedir() -> dict:
    return _get(URL)


def leer(datos) -> Ribbons | None:
    """None si no hay 60 días."""
    lista = datos.get("hashrates") if isinstance(datos, dict) else None
    potencias: dict[date, float] = {}
    for d in lista if isinstance(lista, list) else []:
        try:
            cuando = datetime.fromtimestamp(int(d["timestamp"]), timezone.utc).date()
            potencia = float(d["avgHashrate"]) / EXA
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            continue
        if potencia > 0:
            potencias[cuando] = potencia
    fechas = sorted(potencias)
    valores = [potencias[f] for f in fechas]
    if len(valores) < LARGA:
        return None

    dias = []
    for i in range(LARGA - 1, len(valores)):
        corta = sum(valores[i - CORTA + 1 : i + 1]) / CORTA
        larga = sum(valores[i - LARGA + 1 : i + 1]) / LARGA
        dias.append(Dia(fechas[i], valores[i], corta, larga))
    return Ribbons(dias)
