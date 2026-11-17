"""/pienso: antes de comprar, 24 h para pensarlo y luego te pregunto otra vez."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .puntuales import numero
from .recordar import QUITAR
from .simbolos import a_id

EJEMPLO = "/pienso btc 500"
PLAZO = timedelta(hours=24)

# Lo que ya es mucho para un día: a partir de aquí lo digo con todas las letras.
SUBIDON = 8.0
# Moverse menos de esto en un día es quedarse igual.
IGUAL = 0.5


class PiensoError(Exception):
    """Lo que escribiste en /pienso no se entiende."""


@dataclass(frozen=True)
class Pienso:
    coin_id: str
    importe: float  # lo que quieres meter, en la moneda del .env
    precio: float  # el de cuando lo dijiste
    cuando: datetime

    @property
    def pregunta(self) -> datetime:
        return self.cuando + PLAZO

    def cambio(self, precio: float) -> float:
        return (precio / self.precio - 1) * 100


def interpretar(argumento: str) -> tuple[str, float | None]:
    """'btc 500' -> ('bitcoin', 500). 'btc no' -> ('bitcoin', None): olvidarlo."""
    partes = argumento.split()
    if len(partes) != 2:
        raise PiensoError(f"Escríbelo así: {EJEMPLO} (la cripto y lo que meterías)")
    coin_id = a_id(partes[0])
    if partes[1].lower() in QUITAR:
        return coin_id, None
    importe = numero(partes[1])
    if importe is None or importe <= 0:
        raise PiensoError(f"'{partes[1]}' no es un importe. Por ejemplo: {EJEMPLO}")
    return coin_id, importe


def tocan(lista: list[Pienso], ahora: datetime) -> list[Pienso]:
    return [p for p in lista if ahora >= p.pregunta]


def comando_compra(p: Pienso, precio: float) -> str:
    """El /compra del botón: lo que te da el importe al precio de ahora."""
    # Con coma: numero() leería "1.234" como mil doscientos.
    cantidad = f"{p.importe / precio:.8f}".rstrip("0").rstrip(".").replace(".", ",")
    importe = f"{p.importe:g}".replace(".", ",")
    return f"/compra {p.coin_id} {cantidad} {importe}"


def a_texto(p: Pienso) -> str:
    """Como va en la tabla de ajustes: 'cuando|importe|precio'."""
    return f"{p.cuando.isoformat(timespec='seconds')}|{p.importe!r}|{p.precio!r}"


def de_texto(coin_id: str, texto: str) -> Pienso | None:
    try:
        cuando, importe, precio = texto.split("|")
        return Pienso(
            coin_id, float(importe), float(precio), datetime.fromisoformat(cuando)
        )
    except ValueError:
        return None
