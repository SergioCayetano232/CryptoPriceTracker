"""/exportar: los precios guardados de una cripto, o tus movimientos, en un CSV."""

import csv
from datetime import date, datetime
from io import StringIO

from .ganancias import de_venta
from .movimientos import Movimiento
from .periodo import PeriodoError, leer
from .simbolos import a_id

POR_DEFECTO = 30 * 24

EJEMPLO = "/exportar bitcoin 30d"
EJEMPLO_MOVIMIENTOS = "/exportar movimientos"


def pide_movimientos(argumento: str) -> bool:
    partes = argumento.lower().split()
    if not partes or partes[0] != "movimientos":
        return False
    if len(partes) > 1:
        raise PeriodoError(f"Escríbelo así: {EJEMPLO_MOVIMIENTOS}")
    return True


def movimientos_a_csv(lista: list[Movimiento], currency: str) -> bytes:
    """Del más antiguo al más nuevo, con el mismo formato que el de precios."""
    moneda = currency.lower()
    salida = StringIO()
    # A mano no: una nota con ; o con un salto de línea descolocaría las columnas.
    fichero = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    fichero.writerow(
        [
            "fecha",
            "tipo",
            "cripto",
            "cantidad",
            f"importe_{moneda}",
            f"precio_unidad_{moneda}",
            f"ganancia_{moneda}",
            "nota",
            "numero",
        ]
    )
    for m in sorted(lista, key=lambda m: m.id):
        ganancia = de_venta(m.antes, m.cantidad, m.coste) if m.tipo == "venta" else None
        fichero.writerow(
            [
                m.cuando.astimezone().strftime("%Y-%m-%d %H:%M"),
                m.tipo,
                m.coin_id,
                _numero(m.cantidad),
                _opcional(m.coste),
                _opcional(None if m.coste is None else m.coste / m.cantidad),
                _opcional(ganancia),
                _nota(m.nota),
                m.id,
            ]
        )
    return salida.getvalue().encode("utf-8-sig")


def nombre_movimientos(hoy: date) -> str:
    return f"movimientos-{hoy.isoformat()}.csv"


def _opcional(valor: float | None) -> str:
    return "" if valor is None else _numero(valor)


def _nota(nota: str | None) -> str:
    if not nota:
        return ""
    # Una nota como "-10% y vendo" Excel la tomaría por una fórmula.
    return f"'{nota}" if nota[0] in "=+-@" else nota


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 7d' -> ('bitcoin', 168). Sin tramo, 30 dias."""
    partes = argumento.split()
    if len(partes) not in (1, 2):
        raise PeriodoError(f"Escríbelo así: {EJEMPLO}")

    horas = leer(partes[1]) if len(partes) == 2 else POR_DEFECTO
    return a_id(partes[0]), horas


def a_csv(serie: list[tuple[datetime, float]], currency: str) -> bytes:
    """Con punto y coma, coma decimal y BOM: lo que abre bien un Excel en español."""
    lineas = [f"fecha;precio_{currency.lower()}"]
    for cuando, precio in serie:
        # A la hora de aqui: en UTC las fechas no cuadran con las del exchange.
        fecha = cuando.astimezone().strftime("%Y-%m-%d %H:%M")
        lineas.append(f"{fecha};{_numero(precio)}")
    return ("\r\n".join(lineas) + "\r\n").encode("utf-8-sig")


def nombre_archivo(coin_id: str, horas: float, hoy: date) -> str:
    """bitcoin-30d-2026-10-03.csv"""
    tramo = f"{horas // 24:g}d" if horas % 24 == 0 else f"{horas:g}h"
    return f"{coin_id}-{tramo}-{hoy.isoformat()}.csv"


def _numero(precio: float) -> str:
    # Sin notacion cientifica: 1.2e-05 (lo que vale un SHIB) Excel no lo lee.
    return f"{precio:.10f}".rstrip("0").rstrip(".").replace(".", ",")
