"""Los 👍 y 👎 de debajo de los avisos: lo que te sirvió y lo que te sobraba."""

from dataclasses import dataclass
from datetime import datetime, timezone

from ..nucleo.simbolos import a_id

SI, NO = "si", "no"

# Con menos votos, que sobren la mayoría puede ser un mal día.
MINIMO = 3
# Más de la mitad sobrando ya es para abrir la regla.
MUCHOS = 0.5


class VotoError(Exception):
    """Lo que llega del botón no se entiende."""


@dataclass(frozen=True)
class Voto:
    coin_id: str
    cuando: datetime  # la hora del aviso, no la de pulsar el botón
    util: bool


@dataclass(frozen=True)
class Votos:
    utiles: int = 0
    sobran: int = 0

    @property
    def total(self) -> int:
        return self.utiles + self.sobran

    @property
    def muchos_sobran(self) -> bool:
        return self.total >= MINIMO and self.sobran / self.total > MUCHOS


SIN_VOTOS = Votos()


def datos(coin_id: str, util: bool, cuando: datetime) -> str:
    """Lo que lleva dentro el botón: '/voto bitcoin si 1795000000'."""
    return f"/voto {coin_id} {SI if util else NO} {int(cuando.timestamp())}"


def interpretar(argumento: str) -> Voto:
    """Lo que escribe el botón. A mano no vale: hace falta la hora del aviso."""
    partes = argumento.split()
    if len(partes) != 3 or partes[1] not in (SI, NO) or not partes[2].isdigit():
        raise VotoError(
            "Esto va con los botones 👍 y 👎 de debajo de los avisos, no escrito."
        )
    try:
        cuando = datetime.fromtimestamp(int(partes[2]), timezone.utc)
    except (OverflowError, OSError, ValueError):
        raise VotoError("Ese aviso no sé de cuándo es.") from None
    return Voto(a_id(partes[0]), cuando, partes[1] == SI)


def contar(votos: list[Voto], coin_id: str, desde: datetime | None = None) -> Votos:
    """Los de esa cripto. Con desde, solo los de avisos de ahí en adelante."""
    suyos = [
        v
        for v in votos
        if v.coin_id == coin_id and (desde is None or v.cuando >= desde)
    ]
    utiles = sum(v.util for v in suyos)
    return Votos(utiles, len(suyos) - utiles)
