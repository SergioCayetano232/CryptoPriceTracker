"""/impuestos 2025 csv: cada venta del año con FIFO, para copiarla a la Renta."""

import csv
from dataclasses import dataclass
from datetime import datetime
from io import StringIO

from ..informes.exportar import _numero
from ..inversion.movimientos import Movimiento
from . import fifo


@dataclass(frozen=True)
class Venta:
    numero: int
    cuando: datetime
    coin_id: str
    cantidad: float
    transmision: float | None  # lo que te dieron, ya sin la comisión
    adquisicion: float | None  # lo que costó lo vendido, con FIFO

    @property
    def ganancia(self) -> float | None:
        if self.transmision is None or self.adquisicion is None:
            return None
        return self.transmision - self.adquisicion


def pide_csv(argumento: str) -> tuple[str, bool]:
    """'2025 csv' -> ('2025', True). Lo demás se queda para leer el año."""
    partes = argumento.split()
    if partes and partes[-1].lower() == "csv":
        return " ".join(partes[:-1]), True
    return argumento, False


def ventas(movimientos: list[Movimiento], año: int) -> list[Venta]:
    """movimientos son todos, de cualquier año: el coste sale de compras viejas."""
    return [
        Venta(v.id, v.cuando, v.coin_id, v.cantidad, v.coste, coste)
        for v, coste in fifo.ventas(movimientos)
        if v.cuando.year == año
    ]


def a_csv(lista: list[Venta], currency: str) -> bytes:
    """Una fila por venta y al final el total de las que se pueden contar."""
    moneda = currency.lower()
    salida = StringIO()
    fichero = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    fichero.writerow(
        [
            "fecha_venta",
            "cripto",
            "cantidad",
            f"valor_transmision_{moneda}",
            f"valor_adquisicion_{moneda}",
            f"ganancia_{moneda}",
            "numero",
        ]
    )
    for v in lista:
        fichero.writerow(
            [
                v.cuando.astimezone().strftime("%Y-%m-%d"),
                v.coin_id,
                _numero(v.cantidad),
                _opcional(v.transmision),
                _opcional(v.adquisicion),
                _opcional(v.ganancia),
                v.numero,
            ]
        )
    # Las que no tienen precio no entran: sumarlas a medias daría un total falso.
    contadas = [v for v in lista if v.ganancia is not None]
    if contadas:
        fichero.writerow(
            [
                "total",
                "",
                "",
                _numero(sum(v.transmision for v in contadas)),
                _numero(sum(v.adquisicion for v in contadas)),
                _numero(sum(v.ganancia for v in contadas)),
                "",
            ]
        )
    return salida.getvalue().encode("utf-8-sig")


def nombre(año: int) -> str:
    return f"renta-{año}.csv"


def _opcional(valor: float | None) -> str:
    return "" if valor is None else _numero(valor)
