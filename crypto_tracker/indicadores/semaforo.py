"""/semaforo: una sola luz con lo que dicen el RSI, el MACD, las bandas...

Cada indicador vota a favor de comprar, en contra o se queda en medio. No mezcla
los números: un RSI de 20 y un miedo de 20 no se pueden sumar, sus votos sí.
"""

from dataclasses import dataclass

from .bollinger import Bandas
from .funding import Funding
from .macd import Macd
from .media import lado_de_todas
from .miedo import Indice
from .rsi import SOBRECOMPRA, SOBREVENTA, Rsi

VERDE, AMBAR, ROJO = "verde", "ambar", "rojo"

# Con menos, un solo indicador decidiría el color.
MIN_VOTOS = 3
# Hace falta que ganen por dos: con uno de diferencia sigue siendo un empate.
MARGEN = 2

# Los del índice de miedo: por debajo, miedo extremo; por encima, codicia extrema.
MIEDO, CODICIA = 25, 75
# Del funding, en % por pago: los mismos cortes de /funding.
FUNDING_BAJO, FUNDING_ALTO = -0.01, 0.05


@dataclass(frozen=True)
class Voto:
    nombre: str
    valor: int  # 1 a favor de comprar, -1 en contra, 0 ni una cosa ni otra
    motivo: str


def de_rsi(r: Rsi) -> Voto:
    nombre = f"RSI {r.valor:.0f}"
    if r.valor <= SOBREVENTA:
        return Voto(nombre, 1, "sobrevendida, suele rebotar")
    if r.valor >= SOBRECOMPRA:
        return Voto(nombre, -1, "sobrecomprada, suele frenar")
    return Voto(nombre, 0, "ni pasada de subidas ni de bajadas")


def de_macd(m: Macd) -> Voto:
    # Solo cuenta si va a más: uno que se apaga está a punto de darse la vuelta.
    if not m.cogiendo_fuerza:
        return Voto("MACD", 0, "pierde empuje, sin dirección clara")
    if m.arriba:
        return Voto("MACD", 1, "coge empuje hacia arriba")
    return Voto("MACD", -1, "coge empuje hacia abajo")


def de_bandas(b: Bandas) -> Voto:
    if b.ahora < b.baja:
        return Voto("Bollinger", 1, "por debajo de su banda, más barata de lo normal")
    if b.ahora > b.alta:
        return Voto("Bollinger", -1, "por encima de su banda, más cara de lo normal")
    return Voto("Bollinger", 0, "dentro de su banda")


def de_medias(ahora: float, medias: dict[int, float | None]) -> Voto | None:
    """None si no hay al menos dos medias que comparar."""
    if sum(m is not None for m in medias.values()) < 2:
        return None
    lado = lado_de_todas(ahora, medias)
    if lado is None:
        return Voto("Medias", 0, "entre unas y otras")
    if lado:
        return Voto("Medias", 1, "por encima de todas, tendencia al alza")
    return Voto("Medias", -1, "por debajo de todas, tendencia a la baja")


def de_miedo(i: Indice) -> Voto:
    # Al revés que la gente: se compra mejor con miedo que con euforia.
    nombre = f"Miedo {i.valor}"
    if i.valor <= MIEDO:
        return Voto(nombre, 1, "miedo extremo en el mercado, suele ser buen momento")
    if i.valor >= CODICIA:
        return Voto(nombre, -1, "codicia extrema en el mercado, suele ser mal momento")
    return Voto(nombre, 0, "el mercado, sin extremos")


def de_funding(f: Funding) -> Voto:
    tasa = f.ahora if f.semana is None else f.semana
    if tasa < FUNDING_BAJO:
        return Voto("Funding", 1, "muchos apostando a que baja, a veces rebota")
    if tasa >= FUNDING_ALTO:
        return Voto("Funding", -1, "muy apalancado al alza, así vienen las caídas")
    return Voto("Funding", 0, "los de futuros, tranquilos")


def suma(votos: list[Voto]) -> int:
    return sum(v.valor for v in votos)


def luz(votos: list[Voto]) -> str | None:
    """El color, o None si hay tan pocos votos que no dice nada."""
    if len(votos) < MIN_VOTOS:
        return None
    total = suma(votos)
    if total >= MARGEN:
        return VERDE
    if total <= -MARGEN:
        return ROJO
    return AMBAR
