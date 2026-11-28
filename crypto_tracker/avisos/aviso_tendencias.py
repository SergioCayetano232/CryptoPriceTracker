"""/tendencias avisa: un aviso cuando algo tuyo se pone de moda en CoinGecko."""

import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from ..indicadores.tendencias import Tendencia

# Cada ciclo serían ~8.600 consultas al mes; así son unas 120.
CADA = timedelta(hours=6)
# Una que se pone de moda suele seguir unos días: una vez a la semana basta.
REPETIR = timedelta(days=7)

AVISA = {"avisa", "avisame", "avísame"}
NO = {"no"}
EJEMPLO = "/tendencias avisa"


class AvisoError(Exception):
    """Lo que escribiste en /tendencias no se entiende."""


@dataclass(frozen=True)
class Estado:
    mirado: datetime | None = None
    avisadas: dict[str, datetime] = field(default_factory=dict)


@dataclass(frozen=True)
class Nueva:
    tendencia: Tendencia
    lugar: int  # 1 es la que más se busca


def interpretar(argumento: str) -> bool | None:
    """'' -> None (solo la lista). 'avisa' -> True. 'avisa no' o 'no' -> False."""
    palabras = {p.lower() for p in argumento.split()}
    if not palabras:
        return None
    if palabras <= AVISA | NO and palabras & NO:
        return False
    if palabras <= AVISA:
        return True
    raise AvisoError(
        f"No te entiendo. Para que te avise: {EJEMPLO}. Para quitarlo: {EJEMPLO} no"
    )


def toca_mirar(e: Estado, ahora: datetime) -> bool:
    return e.mirado is None or ahora - e.mirado >= CADA


def nuevas(
    lista: list[Tendencia], mias: set[str], e: Estado, ahora: datetime
) -> list[Nueva]:
    """Las tuyas que están en la lista y no te he contado esta semana."""
    return [
        Nueva(t, lugar)
        for lugar, t in enumerate(lista, 1)
        if t.coin_id in mias
        and (t.coin_id not in e.avisadas or ahora - e.avisadas[t.coin_id] >= REPETIR)
    ]


def mirado(e: Estado, ahora: datetime, avisadas: list[str] = ()) -> Estado:
    """El estado tras mirar, y con las de hoy apuntadas. Las viejas se olvidan."""
    quedan = {c: d for c, d in e.avisadas.items() if ahora - d < REPETIR}
    quedan.update({c: ahora for c in avisadas})
    return replace(e, mirado=ahora, avisadas=quedan)


def a_texto(e: Estado) -> str:
    return json.dumps(
        {
            "mirado": e.mirado.isoformat() if e.mirado else None,
            "avisadas": {c: d.isoformat() for c, d in e.avisadas.items()},
        }
    )


def de_texto(texto: str) -> Estado:
    """Si está roto, como recién puesto: lo peor es un aviso de más."""
    try:
        datos = json.loads(texto)
        return Estado(
            datetime.fromisoformat(datos["mirado"]) if datos.get("mirado") else None,
            {
                c: datetime.fromisoformat(d)
                for c, d in (datos.get("avisadas") or {}).items()
            },
        )
    except (ValueError, TypeError, AttributeError, KeyError):
        return Estado()
