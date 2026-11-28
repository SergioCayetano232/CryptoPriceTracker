"""/prediccion: dices a cuánto estará el domingo y llevo tu marcador."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from .avisos.puntuales import numero
from .avisos.recordar import QUITAR
from .nucleo.simbolos import a_id

EJEMPLO = "/prediccion btc 70000"

# El domingo a esta hora, en la hora de aquí, se mira cómo ha quedado.
HORA = time(20, 0)
DOMINGO = 6
# Apostar el domingo a las siete es casi ver el resultado: pasa al siguiente.
MARGEN = timedelta(hours=24)


class PrediccionError(Exception):
    """Lo que escribiste en /prediccion no se entiende."""


@dataclass(frozen=True)
class Prediccion:
    id: int | None
    coin_id: str
    hecha: datetime
    cierre: datetime
    entonces: float  # el precio cuando la hiciste
    predicho: float
    real: float | None = None  # None hasta el domingo

    @property
    def error(self) -> float:
        """Lo que te fuiste, en % del precio de verdad."""
        return abs(self.predicho - self.real) / self.real * 100

    @property
    def error_quieto(self) -> float:
        """Lo que se habría ido decir "se queda como está"."""
        return abs(self.entonces - self.real) / self.real * 100

    @property
    def acierta_lado(self) -> bool:
        """Si dijiste que subía y subió, o al revés."""
        return (self.predicho > self.entonces) == (self.real > self.entonces)

    @property
    def gana_al_quieto(self) -> bool:
        return self.error < self.error_quieto


@dataclass(frozen=True)
class Marcador:
    total: int
    lado: int  # las que acertaste hacia dónde iba
    error_medio: float
    al_quieto: int  # las que te acercaste más que "se queda igual"

    @property
    def mejor_que_moneda(self) -> bool | None:
        """Una moneda acierta el lado la mitad de las veces. None si son pocas."""
        if self.total < 4:
            return None
        return self.lado / self.total > 0.5


def interpretar(argumento: str) -> tuple[str, float | None]:
    """'btc 70000' -> ('bitcoin', 70000). 'btc no' -> ('bitcoin', None)."""
    partes = argumento.split()
    if len(partes) != 2:
        raise PrediccionError(f"Escríbelo así: {EJEMPLO} (a cuánto estará el domingo)")
    coin_id = a_id(partes[0])
    if partes[1].lower() in QUITAR:
        return coin_id, None
    valor = numero(partes[1])
    if valor is None or valor <= 0:
        raise PrediccionError(f"'{partes[1]}' no es un precio. Por ejemplo: {EJEMPLO}")
    return coin_id, valor


def cierre(ahora: datetime) -> datetime:
    """El domingo a las HORA en que se mira, con al menos MARGEN por delante."""
    local = ahora.astimezone()
    dias = (DOMINGO - local.weekday()) % 7
    domingo = datetime.combine(
        local.date() + timedelta(days=dias), HORA, tzinfo=local.tzinfo
    )
    if domingo - local < MARGEN:
        domingo += timedelta(days=7)
    return domingo


# Lo más lejos del domingo a las HORA que acepto como su precio.
CERCA = timedelta(hours=2)


def precio_del_cierre(
    serie: list[tuple[datetime, float]], cuando: datetime
) -> float | None:
    """El precio guardado más cerca del cierre. None si no hay ninguno cerca."""
    cerca = [(abs(t - cuando), p) for t, p in serie if abs(t - cuando) <= CERCA]
    return min(cerca)[1] if cerca else None


def tocan(lista: list[Prediccion], ahora: datetime) -> list[Prediccion]:
    return [p for p in lista if p.real is None and ahora >= p.cierre]


def marcador(lista: list[Prediccion]) -> Marcador | None:
    hechas = [p for p in lista if p.real is not None]
    if not hechas:
        return None
    return Marcador(
        len(hechas),
        sum(p.acierta_lado for p in hechas),
        sum(p.error for p in hechas) / len(hechas),
        sum(p.gana_al_quieto for p in hechas),
    )
