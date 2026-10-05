"""/exportar: los precios guardados de una cripto, en un CSV."""

from datetime import date, datetime

from .periodo import PeriodoError, leer
from .simbolos import a_id

POR_DEFECTO = 30 * 24

EJEMPLO = "/exportar bitcoin 30d"


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
