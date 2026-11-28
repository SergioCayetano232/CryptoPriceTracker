"""/tarjeta: cómo va tu cartera en una imagen para enseñar, solo con porcentajes."""

from dataclasses import dataclass
from datetime import date, datetime

from ..inversion.cartera import Valor, total
from ..inversion.reparto import Trozo, trozos
from ..nucleo.periodo import PeriodoError, es_tramo, leer

EJEMPLO = "/tarjeta o /tarjeta 90d"
HORAS = 30 * 24
# Más puntos no se notan en la imagen y con 90 días hay decenas de miles.
PUNTOS = 200


@dataclass(frozen=True)
class Tarjeta:
    total: float | None  # % sobre lo metido; None si no sé lo que costó todo
    tramo: float | None  # % en el tramo; None sin dos precios guardados
    horas: float
    linea: list[float]  # la serie en % desde su primer punto: dibuja sin cifras
    reparto: list[Trozo]
    dia: date


def interpretar(argumento: str) -> float:
    texto = argumento.strip()
    if not texto:
        return HORAS
    if not es_tramo(texto):
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")
    return leer(texto)


def reducir(valores: list[float], puntos: int = PUNTOS) -> list[float]:
    """Se queda con unos cuantos repartidos, siempre con el primero y el último."""
    if len(valores) <= puntos:
        return valores
    paso = (len(valores) - 1) / (puntos - 1)
    return [valores[round(i * paso)] for i in range(puntos)]


def calcular(
    valores: list[Valor],
    serie: list[tuple[datetime, float]],
    horas: float,
    hoy: date,
) -> Tarjeta | None:
    """None si la cartera no vale nada: no hay nada que enseñar."""
    suma = total(valores)
    if suma.valor <= 0:
        return None

    linea, tramo = [], None
    if len(serie) >= 2 and serie[0][1] > 0:
        inicio = serie[0][1]
        linea = reducir([(v / inicio - 1) * 100 for _, v in serie])
        tramo = linea[-1]
    return Tarjeta(
        total=suma.porcentaje,
        tramo=tramo,
        horas=horas,
        linea=linea,
        reparto=trozos(valores),
        dia=hoy,
    )
