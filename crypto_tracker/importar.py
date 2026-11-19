"""/importar: las compras y ventas del CSV de Binance (historial de operaciones)."""

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import simbolos

COLUMNAS = ("Date(UTC)", "Pair", "Side", "Price", "Executed", "Amount", "Fee")

# Con usd valen también las estables: en Binance casi nadie opera contra USD a secas.
CONTRAPARTES = {
    "eur": {"EUR"},
    "usd": {"USD", "USDT", "USDC", "FDUSD"},
}

# "0.00100000BTC" o "55,000.00": la cifra con la moneda pegada detrás.
_CIFRA = re.compile(r"^([0-9][0-9.,]*)\s*([A-Z0-9]*)$")


class ImportarError(Exception):
    """El archivo no es el historial de Binance."""


@dataclass(frozen=True)
class Operacion:
    cuando: datetime
    coin_id: str
    tipo: str  # "compra" o "venta"
    cantidad: float
    coste: float  # lo que pagaste o te dieron, ya con la comisión
    comision: float | None = None  # None si la cobraron en BNB u otra


@dataclass(frozen=True)
class Lectura:
    operaciones: list[Operacion]
    # el motivo y cuántas: {"contra BTC": 3, "no sé qué es PEPE": 1}
    saltadas: dict[str, int] = field(default_factory=dict)
    sin_comision: int = 0  # las que la pagaron en otra moneda


def _cifra(texto: str) -> tuple[float, str]:
    hallado = _CIFRA.match(texto.strip().upper())
    if not hallado:
        raise ValueError(texto)
    # Binance pone la coma de los miles, nunca la de los decimales.
    return float(hallado[1].replace(",", "")), hallado[2]


def leer_binance(texto: str, vs_currency: str) -> Lectura:
    """De más vieja a más nueva, que es como hay que apuntarlas."""
    filas = csv.DictReader(io.StringIO(texto.lstrip("﻿")))
    if not filas.fieldnames or not set(COLUMNAS) <= {
        c.strip() for c in filas.fieldnames
    }:
        raise ImportarError(
            "No parece el historial de operaciones de Binance. Lo saco en "
            "Órdenes → Historial de operaciones → Exportar."
        )

    validas = CONTRAPARTES.get(vs_currency.lower(), {vs_currency.upper()})
    operaciones = []
    saltadas: dict[str, int] = {}
    sin_comision = 0

    def saltar(motivo: str) -> None:
        saltadas[motivo] = saltadas.get(motivo, 0) + 1

    for fila in filas:
        fila = {k.strip(): (v or "").strip() for k, v in fila.items() if k}
        try:
            cuando = datetime.strptime(fila["Date(UTC)"], "%Y-%m-%d %H:%M:%S")
            precio, _ = _cifra(fila["Price"])
            ejecutado, base = _cifra(fila["Executed"])
            importe, contra = _cifra(fila["Amount"])
            pagada, moneda_comision = _cifra(fila["Fee"] or "0")
        except (KeyError, ValueError):
            saltar("filas que no entiendo")
            continue

        lado = fila["Side"].upper()
        if lado not in ("BUY", "SELL") or ejecutado <= 0:
            saltar("filas que no entiendo")
            continue
        # Las exportaciones viejas no pegan la moneda a la cifra: sale del par.
        par = fila["Pair"].upper()
        if not contra:
            contra = next((v for v in validas if par.endswith(v)), "")
        if not base:
            base = par.removesuffix(contra)
        if contra not in validas:
            saltar(f"en {contra or par}, no en {vs_currency.upper()}")
            continue
        coin_id = simbolos.IDS.get(base.lower())
        if coin_id is None:
            saltar(f"no sé qué es {base}")
            continue

        cantidad, coste, comision = ejecutado, importe, None
        if moneda_comision == base:
            comision = pagada * precio
            # en la compra te llega menos cripto; en la venta te quitan de más
            cantidad += -pagada if lado == "BUY" else pagada
        elif moneda_comision in ("", contra):
            comision = pagada
            coste += pagada if lado == "BUY" else -pagada
        else:
            sin_comision += 1

        operaciones.append(
            Operacion(
                cuando=cuando.replace(tzinfo=timezone.utc),
                coin_id=coin_id,
                tipo="compra" if lado == "BUY" else "venta",
                cantidad=cantidad,
                coste=coste,
                comision=comision or None,
            )
        )

    operaciones.sort(key=lambda o: o.cuando)
    return Lectura(operaciones, saltadas, sin_comision)
