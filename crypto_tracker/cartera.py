"""Cuanto vale lo que tienes y cuanto llevas ganado o perdido."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import groupby

from .config import Posicion

# Si de una cripto no hay precio en este rato, ese punto no se dibuja: tirar de
# un precio de hace dias pintaria un valor que nunca tuviste.
HUECO_MAXIMO = timedelta(hours=1)


@dataclass(frozen=True)
class Valor:
    coin_id: str
    valor: float
    invertido: float | None = None

    @property
    def ganancia(self) -> float | None:
        return None if self.invertido is None else self.valor - self.invertido

    @property
    def porcentaje(self) -> float | None:
        if not self.invertido:
            return None
        return self.ganancia / self.invertido * 100


def valorar(
    posiciones: list[Posicion], precios: dict[str, float]
) -> tuple[list[Valor], list[str]]:
    """Valora cada posicion. Devuelve tambien las que se quedaron sin precio."""
    valores, faltan = [], []

    for p in posiciones:
        precio = precios.get(p.coin_id)
        if precio is None:
            faltan.append(p.coin_id)
            continue
        valores.append(Valor(p.coin_id, p.cantidad * precio, p.invertido))

    return valores, faltan


def total(valores: list[Valor]) -> Valor:
    """La suma. Si alguna no dice lo que costo, el total tampoco puede."""
    invertido = None
    if valores and all(v.invertido is not None for v in valores):
        invertido = sum(v.invertido for v in valores)
    return Valor("total", sum(v.valor for v in valores), invertido)


def valor_total(posiciones: list[Posicion], precios: dict[str, float]) -> float | None:
    """Lo que vale todo junto. None si falta el precio de alguna."""
    # Un total sin una de ellas parece una caida, y daria una alerta falsa.
    valores, faltan = valorar(posiciones, precios)
    if not posiciones or faltan:
        return None
    return sum(v.valor for v in valores)


def serie_valor(
    posiciones: list[Posicion], filas: list[tuple[datetime, str, float]]
) -> list[tuple[datetime, float]]:
    """Lo que habria valido lo que tienes ahora en cada momento guardado.

    filas son (cuando, cripto, precio) ordenadas por fecha. Las de una misma
    consulta comparten hora, asi que se juntan por hora.
    """
    cantidades = {p.coin_id: p.cantidad for p in posiciones}
    if not cantidades:
        return []

    ultimo: dict[str, tuple[datetime, float]] = {}
    serie = []
    for cuando, grupo in groupby(filas, key=lambda f: f[0]):
        for _, coin_id, precio in grupo:
            if coin_id in cantidades:
                ultimo[coin_id] = (cuando, precio)

        al_dia = all(
            c in ultimo and cuando - ultimo[c][0] <= HUECO_MAXIMO for c in cantidades
        )
        if al_dia:
            valor = sum(cantidades[c] * ultimo[c][1] for c in cantidades)
            serie.append((cuando, valor))

    return serie
