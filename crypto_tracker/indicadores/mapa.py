"""/mapa: las más grandes en recuadros, cada uno del tamaño de lo que vale."""

import math
from dataclasses import dataclass

from .altseason import cuenta

# Con más, las pequeñas salen tan finas que no cabe ni el nombre.
CUANTAS = 30
# Quitando estables y copias de las 60 primeras siempre quedan más de 30.
PEDIR = 60


@dataclass(frozen=True)
class Casilla:
    coin_id: str
    simbolo: str
    capital: float
    variacion: float  # en 24 h


@dataclass(frozen=True)
class Mapa:
    casillas: list[Casilla]  # de la más grande a la más pequeña

    @property
    def suben(self) -> int:
        return sum(c.variacion > 0 for c in self.casillas)

    @property
    def bajan(self) -> int:
        return sum(c.variacion < 0 for c in self.casillas)

    @property
    def media(self) -> float:
        """Lo que se ha movido el conjunto, pesando cada una por lo que vale."""
        total = sum(c.capital for c in self.casillas)
        return sum(c.variacion * c.capital for c in self.casillas) / total


def leer(datos) -> Mapa | None:
    """De /coins/markets en dólares, con el 30d para poder quitar los fondos."""
    lista = []
    for m in datos if isinstance(datos, list) else []:
        if not isinstance(m, dict) or not m.get("id"):
            continue
        capital = _numero(m.get("market_cap"))
        variacion = _numero(m.get("price_change_percentage_24h"))
        precio = _numero(m.get("current_price"))
        if not capital or capital < 0 or variacion is None or precio is None:
            continue
        simbolo = str(m.get("symbol") or "")
        mes = _numero(m.get("price_change_percentage_30d_in_currency"))
        if not cuenta(simbolo, str(m.get("name") or ""), precio, mes or 0.0):
            continue
        lista.append(Casilla(m["id"], simbolo.upper(), capital, variacion))

    lista = sorted(lista, key=lambda c: -c.capital)[:CUANTAS]
    return Mapa(lista) if lista else None


def repartir(
    valores: list[float], ancho: float, alto: float
) -> list[tuple[float, float, float, float]]:
    """(x, y, ancho, alto) de cada valor, ya ordenados de mayor a menor.

    Va llenando por filas y cierra una en cuanto añadir otra dejaría los
    recuadros más alargados: así salen lo más cuadrados posible.
    """
    total = sum(valores)
    areas = [v / total * ancho * alto for v in valores]
    x = y = 0.0
    rects = []
    while areas:
        lado = min(ancho, alto)
        fila = [areas[0]]
        while len(fila) < len(areas) and _peor(
            fila + [areas[len(fila)]], lado
        ) <= _peor(fila, lado):
            fila.append(areas[len(fila)])
        areas = areas[len(fila) :]

        suma = sum(fila)
        if ancho >= alto:
            # Una columna a la izquierda, de arriba abajo.
            grosor = suma / alto
            dy = y
            for a in fila:
                rects.append((x, dy, grosor, a / grosor))
                dy += a / grosor
            x += grosor
            ancho -= grosor
        else:
            # Una fila arriba, de izquierda a derecha.
            grosor = suma / ancho
            dx = x
            for a in fila:
                rects.append((dx, y, a / grosor, grosor))
                dx += a / grosor
            y += grosor
            alto -= grosor
    return rects


def _peor(fila: list[float], lado: float) -> float:
    """Lo alargado del recuadro más alargado si la fila va contra ese lado."""
    suma = sum(fila)
    return max(max(lado**2 * a / suma**2, suma**2 / (lado**2 * a)) for a in fila)


def _numero(valor) -> float | None:
    if isinstance(valor, (int, float)) and math.isfinite(valor):
        return float(valor)
    return None
