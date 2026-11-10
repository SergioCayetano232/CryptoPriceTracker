"""/arrepentido: lo que valdría hoy lo que vendiste, contra lo que te dieron."""

from dataclasses import dataclass

from .movimientos import Movimiento


@dataclass(frozen=True)
class Vendida:
    coin_id: str
    cantidad: float
    cobrado: float
    hoy: float  # lo que te darían ahora por lo mismo

    @property
    def diferencia(self) -> float:
        """Positiva si vendiste pronto: hoy te darían más."""
        return self.hoy - self.cobrado


@dataclass(frozen=True)
class Arrepentido:
    vendidas: list[Vendida]  # la que más duele primero
    sin_datos: int

    @property
    def total(self) -> float:
        return sum(v.diferencia for v in self.vendidas)


def calcular(ventas: list[Movimiento], precios: dict[str, float]) -> Arrepentido:
    cantidades: dict[str, float] = {}
    cobrados: dict[str, float] = {}
    sin_datos = 0
    for v in ventas:
        # Las de antes de apuntar a cuánto vendías no sirven para comparar.
        if v.coste is None or v.coin_id not in precios:
            sin_datos += 1
            continue
        cantidades[v.coin_id] = cantidades.get(v.coin_id, 0) + v.cantidad
        cobrados[v.coin_id] = cobrados.get(v.coin_id, 0) + v.coste

    vendidas = [
        Vendida(c, cantidades[c], cobrados[c], cantidades[c] * precios[c])
        for c in cantidades
    ]
    vendidas.sort(key=lambda v: v.diferencia, reverse=True)
    return Arrepentido(vendidas, sin_datos)
