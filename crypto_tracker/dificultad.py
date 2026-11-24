"""/dificultad: cuándo toca el próximo ajuste de bitcoin y cómo va el minado."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .comisionred import ComisionRedError, _get

AJUSTE_URL = "https://mempool.space/api/v1/difficulty-adjustment"
POTENCIA_URL = "https://mempool.space/api/v1/mining/hashrate/3m"

BLOQUES = 2016
MINUTOS = 10
EXA = 1e18

# Una caída así en un mes es que a muchos mineros no les salen las cuentas.
CAPITULACION = -10.0

EJEMPLO = "/dificultad"

# El mismo error que /comisionred: es el mismo sitio.
DificultadError = ComisionRedError


@dataclass(frozen=True)
class Dificultad:
    progreso: float  # % de los 2016 bloques del tramo
    cambio: float  # lo que se espera que cambie, en %
    anterior: float | None  # lo que cambió en el último ajuste
    faltan: int  # bloques
    cuando: datetime  # la hora estimada del ajuste
    cada: float  # minutos entre bloques en este tramo
    potencia: list[float]  # EH/s de cada día, del más viejo a hoy

    @property
    def potencia_mes(self) -> float | None:
        """% que ha cambiado el hashrate en 30 días."""
        if len(self.potencia) <= 30:
            return None
        return (self.potencia[-1] / self.potencia[-31] - 1) * 100

    @property
    def capitulacion(self) -> bool:
        mes = self.potencia_mes
        return mes is not None and mes <= CAPITULACION


def pedir() -> tuple[dict, dict]:
    """El ajuste y el hashrate. Sin el hashrate sigue, que es lo de menos."""
    ajuste = _get(AJUSTE_URL)
    try:
        potencia = _get(POTENCIA_URL)
    except DificultadError:
        potencia = {}
    return ajuste, potencia


def _numero(valor) -> float | None:
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        return None
    return float(valor)


def leer(ajuste, potencia) -> Dificultad | None:
    """None si el ajuste no trae lo que hace falta."""
    a = ajuste if isinstance(ajuste, dict) else {}
    progreso = _numero(a.get("progressPercent"))
    cambio = _numero(a.get("difficultyChange"))
    faltan = _numero(a.get("remainingBlocks"))
    fecha = _numero(a.get("estimatedRetargetDate"))
    cada = _numero(a.get("timeAvg"))
    if None in (progreso, cambio, faltan, fecha) or not cada or cada <= 0:
        return None

    p = potencia if isinstance(potencia, dict) else {}
    dias = [
        (d["timestamp"], d["avgHashrate"] / EXA)
        for d in p.get("hashrates") or []
        if isinstance(d, dict)
        and _numero(d.get("timestamp")) is not None
        and (_numero(d.get("avgHashrate")) or 0) > 0
    ]
    return Dificultad(
        progreso=min(max(progreso, 0), 100),
        cambio=cambio,
        anterior=_numero(a.get("previousRetarget")),
        faltan=int(faltan),
        cuando=datetime.fromtimestamp(fecha / 1000, timezone.utc),
        cada=cada / 60_000,
        potencia=[h for _, h in sorted(dias)],
    )


def falta(cuando: datetime, ahora: datetime) -> str:
    """'2 días y 7 h', '5 h', 'menos de una hora'."""
    resto = cuando - ahora
    if resto < timedelta(hours=1):
        return "menos de una hora"
    dias, horas = resto.days, resto.seconds // 3600
    if not dias:
        return f"{horas} h"
    texto = "1 día" if dias == 1 else f"{dias} días"
    return f"{texto} y {horas} h" if horas else texto
