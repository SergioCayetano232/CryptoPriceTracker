"""/modelo721: si te toca declarar a Hacienda las criptos que tienes fuera de España."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from ..movimientos import Movimiento
from ..nucleo.config import Posicion

LIMITE = 50_000
# Ya presentado, solo vuelve a tocar si sube más que esto desde lo declarado.
SUBIDA = 20_000


@dataclass(frozen=True)
class Modelo721:
    hoy: float
    en_plazo: bool
    # Lo que valía el 31 de diciembre. None fuera de plazo o si no lo tengo guardado
    cierre: float | None
    año: int  # el del 31 de diciembre que cuenta: el pasado en plazo, este si no
    dias: int  # los que quedan para el próximo 31 de marzo

    @property
    def falta(self) -> float:
        return LIMITE - self.hoy

    @property
    def toca(self) -> bool:
        return self.cierre is not None and self.cierre > LIMITE


def en_plazo(hoy: date) -> bool:
    """Del 1 de enero al 31 de marzo se presenta lo del año anterior."""
    return hoy <= date(hoy.year, 3, 31)


def cierre(año: int) -> datetime:
    # Las 23:59 del 31 de diciembre en España son las 22:59 en UTC.
    return datetime(año, 12, 31, 22, 59, tzinfo=timezone.utc)


def cartera_en(
    ahora: list[Posicion], movimientos: list[Movimiento], cuando: datetime
) -> list[Posicion]:
    """Lo que tenías en ese momento: el 'antes' del primer movimiento de después."""
    antes: dict[str, Posicion | None] = {}
    for m in sorted(movimientos, key=lambda m: m.cuando):
        if m.cuando > cuando and m.coin_id not in antes:
            antes[m.coin_id] = m.antes
    tenias = {p.coin_id: p for p in ahora if p.coin_id not in antes}
    tenias |= {c: p for c, p in antes.items() if p}
    return list(tenias.values())


def calcular(valor_hoy: float, valor_cierre: float | None, hoy: date) -> Modelo721:
    if en_plazo(hoy):
        dias = (date(hoy.year, 3, 31) - hoy).days
        return Modelo721(valor_hoy, True, valor_cierre, hoy.year - 1, dias)
    dias = (date(hoy.year + 1, 3, 31) - hoy).days
    return Modelo721(valor_hoy, False, None, hoy.year, dias)


def toca_avisar(valor: float | None, avisado: date | None, hoy: date) -> bool:
    """Una vez al año, la primera vez que pasa del límite."""
    if valor is None or valor <= LIMITE:
        return False
    return avisado is None or avisado.year != hoy.year


def horas_desde(cuando: datetime, ahora: datetime) -> int:
    return int((ahora - cuando) / timedelta(hours=1))
