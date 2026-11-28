"""/stop: avisa al perder o ganar un % sobre lo que te costó, no sobre lo de ahora."""

from dataclasses import dataclass

from .cartera import Valor
from .nucleo.config import Posicion
from .nucleo.simbolos import a_id
from .puntuales import CARTERA, numero

EJEMPLO = "/stop eth -15%"
EJEMPLO_MOVIL = "/stop eth -10% movil"
MOVIL = ("movil", "móvil", "sigue", "trailing")
FINAL_NOTA = "% sobre lo que te costó"


class StopError(Exception):
    """Lo que escribiste en /stop no se entiende o no se puede calcular."""


@dataclass(frozen=True)
class Stop:
    coin_id: str
    porcentaje: float
    coste: float  # el precio medio; en la cartera, todo lo que metiste
    ahora: float  # el precio; en la cartera, lo que vale

    @property
    def objetivo(self) -> float:
        return self.coste * (1 + self.porcentaje / 100)

    @property
    def sube(self) -> bool:
        return self.porcentaje > 0

    @property
    def llevas(self) -> float:
        return (self.ahora / self.coste - 1) * 100

    @property
    def ya_llego(self) -> bool:
        if self.sube:
            return self.ahora >= self.objetivo
        return self.ahora <= self.objetivo

    @property
    def nota(self) -> str:
        """Lo que sale en /alertas y en el aviso, para que no parezca una normal."""
        pct = f"{self.porcentaje:+g}".replace(".", ",")
        return f"Stop: {pct}{FINAL_NOTA}"


def porcentaje_de_nota(nota: str | None) -> float | None:
    """'Stop: -15% sobre lo que te costó' -> -15.0. Para los /stop más viejos."""
    if not nota or not nota.startswith("Stop: ") or not nota.endswith(FINAL_NOTA):
        return None
    texto = nota.removeprefix("Stop: ").removesuffix(FINAL_NOTA)
    try:
        return float(texto.replace(",", "."))
    except ValueError:
        return None


def separar_movil(argumento: str) -> tuple[str, bool]:
    """'eth -10% movil' -> ('eth -10%', True)."""
    partes = argumento.split()
    if len(partes) == 3 and partes[2].lower() in MOVIL:
        return " ".join(partes[:2]), True
    return argumento, False


def objetivo_movil(maximo: float, porcentaje: float) -> float:
    """porcentaje va en negativo, como en /stop: -10 es un 10% por debajo."""
    return maximo * (1 + porcentaje / 100)


def subir(objetivo: float, porcentaje: float, precio: float) -> float | None:
    """El objetivo nuevo si el precio ha marcado otro máximo. Si no, None."""
    nuevo = objetivo_movil(precio, porcentaje)
    return nuevo if nuevo > objetivo else None


def nota_movil(porcentaje: float) -> str:
    pct = f"{porcentaje:+g}".replace(".", ",")
    return f"Stop móvil: {pct}% desde lo más alto"


def coste(coin_id: str, posiciones: list[Posicion]) -> float | None:
    """Lo que te costó ahora mismo: el precio medio, o todo lo metido en la cartera."""
    if coin_id == CARTERA:
        if not posiciones or any(p.invertido is None for p in posiciones):
            return None
        return sum(p.invertido for p in posiciones)
    for p in posiciones:
        if p.coin_id == coin_id and p.invertido and p.cantidad:
            return p.invertido / p.cantidad
    return None


def seguir(
    objetivo: float, porcentaje: float, coin_id: str, posiciones: list[Posicion]
) -> float | None:
    """El objetivo nuevo si has comprado o vendido desde que lo pusiste. Si no, None."""
    nuevo_coste = coste(coin_id, posiciones)
    # Si ya no la tienes, lo dejo donde estaba en vez de quitarlo sin avisar.
    if nuevo_coste is None:
        return None
    nuevo = nuevo_coste * (1 + porcentaje / 100)
    # Los decimales del precio medio bailan un poco; eso no es haber comprado.
    if abs(nuevo - objetivo) <= abs(objetivo) * 1e-9:
        return None
    return nuevo


def interpretar(argumento: str) -> tuple[str, float]:
    """'eth -15%' -> ('ethereum', -15.0)."""
    partes = argumento.split()
    if len(partes) != 2 or not partes[1].endswith("%"):
        raise StopError(f"Escríbelo así: {EJEMPLO}")

    texto = partes[1][:-1]
    # Aquí no hay "desde ahora" que valga: sin signo no sé si es pérdida o ganancia.
    if not texto.startswith(("+", "-")):
        raise StopError(f"¿Perder o ganar? Pon -{texto}% o +{texto}%")

    porcentaje = numero(texto[1:])
    if porcentaje is None or porcentaje <= 0:
        raise StopError(f"'{partes[1]}' no es un porcentaje. Ej: {EJEMPLO}")
    if texto.startswith("-"):
        porcentaje = -porcentaje
    if porcentaje <= -100:
        raise StopError("No puedes perder un 100 % o más, se quedaría en nada.")

    return a_id(partes[0]), porcentaje


def calcular(coin_id: str, porcentaje: float, valor: Valor) -> Stop:
    if coin_id == CARTERA:
        coste, ahora = valor.invertido, valor.valor
        falta = "Para eso necesito lo que te costó cada una de tu cartera"
    else:
        coste, ahora = valor.precio_medio, valor.precio
        falta = "Para eso necesito lo que te costó"
    if not coste or ahora is None:
        raise StopError(f"{falta}. Apúntalo así: /compra bitcoin 0.01 600")
    return Stop(coin_id, porcentaje, coste, ahora)
