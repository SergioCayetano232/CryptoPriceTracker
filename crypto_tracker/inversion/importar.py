"""/importar: las compras y ventas del CSV de Binance o de Kraken."""

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..nucleo import simbolos

COLUMNAS = ("Date(UTC)", "Pair", "Side", "Price", "Executed", "Amount", "Fee")
COLUMNAS_KRAKEN = ("txid", "pair", "time", "type", "price", "cost", "fee", "vol")

# Con usd valen también las estables: en Binance casi nadie opera contra USD a secas.
CONTRAPARTES = {
    "eur": {"EUR"},
    "usd": {"USD", "USDT", "USDC", "FDUSD"},
}

# En Kraken, las de siempre llevan una X (o una Z si es dinero) delante, y el
# bitcoin es XBT: XXBTZEUR es BTC contra EUR.
_KRAKEN_ALIAS = {"XBT": "BTC", "XDG": "DOGE"}
# Las largas primero: XBTUSDT tiene que dar USDT, no USD.
_KRAKEN_CONTRA = (
    "ZEUR",
    "ZUSD",
    "ZGBP",
    "XXBT",
    "XETH",
    "USDT",
    "USDC",
    "EUR",
    "USD",
    "GBP",
    "XBT",
    "ETH",
)

# "0.00100000BTC" o "55,000.00": la cifra con la moneda pegada detrás.
_CIFRA = re.compile(r"^([0-9][0-9.,]*)\s*([A-Z0-9]*)$")


class ImportarError(Exception):
    """El archivo no es el historial de Binance ni el de Kraken."""


@dataclass(frozen=True)
class Operacion:
    cuando: datetime
    coin_id: str
    tipo: str  # "compra" o "venta"
    cantidad: float
    coste: float  # lo que pagaste o te dieron, ya con la comisión
    comision: float | None = None  # None si la cobraron en BNB u otra
    origen: str = "Binance"  # el exchange, va en la nota del movimiento


@dataclass(frozen=True)
class Lectura:
    operaciones: list[Operacion]
    # el motivo y cuántas: {"contra BTC": 3, "no sé qué es PEPE": 1}
    saltadas: dict[str, int] = field(default_factory=dict)
    sin_comision: int = 0  # las que la pagaron en otra moneda
    origen: str = "Binance"  # de qué exchange es, va en la nota de cada una


def _cifra(texto: str) -> tuple[float, str]:
    hallado = _CIFRA.match(texto.strip().upper())
    if not hallado:
        raise ValueError(texto)
    # Binance pone la coma de los miles, nunca la de los decimales.
    return float(hallado[1].replace(",", "")), hallado[2]


def leer(texto: str, vs_currency: str) -> Lectura:
    """El CSV que sea: lo distingue por las columnas."""
    texto = texto.lstrip("\ufeff")
    cabecera = {c.strip() for c in next(csv.reader(io.StringIO(texto)), [])}
    if set(COLUMNAS_KRAKEN) <= cabecera:
        return leer_kraken(texto, vs_currency)
    if set(COLUMNAS) <= cabecera:
        return leer_binance(texto, vs_currency)
    raise ImportarError(
        "No parece el historial de operaciones de Binance ni el de Kraken. "
        "Mira /importar para ver de dónde se saca."
    )


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


def _activo_kraken(codigo: str) -> str:
    """XXBT -> BTC, XETH -> ETH, ZEUR -> EUR. Los nuevos ya vienen limpios."""
    codigo = _KRAKEN_ALIAS.get(codigo, codigo)
    if len(codigo) == 4 and codigo[0] in "XZ" and codigo.lower() not in simbolos.IDS:
        codigo = _KRAKEN_ALIAS.get(codigo[1:], codigo[1:])
    return codigo


def _par_kraken(par: str) -> tuple[str, str] | None:
    """'XXBTZEUR' o 'XBT/EUR' -> ('BTC', 'EUR'). None si no se sabe partir."""
    par = par.upper()
    if "/" in par:
        base, _, contra = par.partition("/")
    else:
        contra = next((c for c in _KRAKEN_CONTRA if par.endswith(c)), "")
        base = par.removesuffix(contra) if contra else ""
    if not base or not contra:
        return None
    return _activo_kraken(base), _activo_kraken(contra)


def leer_kraken(texto: str, vs_currency: str) -> Lectura:
    """El trades.csv de Kraken (Historial → Exportar → Operaciones)."""
    filas = csv.DictReader(io.StringIO(texto.lstrip("\ufeff")))
    validas = CONTRAPARTES.get(vs_currency.lower(), {vs_currency.upper()})
    operaciones = []
    saltadas: dict[str, int] = {}

    def saltar(motivo: str) -> None:
        saltadas[motivo] = saltadas.get(motivo, 0) + 1

    for fila in filas:
        fila = {k.strip(): (v or "").strip() for k, v in fila.items() if k}
        try:
            # Trae diezmilésimas de segundo y Python 3.10 no las lee: fuera.
            cuando = datetime.strptime(fila["time"][:19], "%Y-%m-%d %H:%M:%S")
            cantidad = float(fila["vol"])
            importe = float(fila["cost"])
            comision = float(fila["fee"] or 0)
            margen = float(fila.get("margin") or 0)
        except (KeyError, ValueError):
            saltar("filas que no entiendo")
            continue

        lado = fila["type"].lower()
        par = _par_kraken(fila["pair"])
        if lado not in ("buy", "sell") or cantidad <= 0 or par is None:
            saltar("filas que no entiendo")
            continue
        # Con margen no compras la cripto de verdad: no es de la cartera.
        if margen:
            saltar("con margen")
            continue
        base, contra = par
        if contra not in validas:
            saltar(f"en {contra}, no en {vs_currency.upper()}")
            continue
        coin_id = simbolos.IDS.get(base.lower())
        if coin_id is None:
            saltar(f"no sé qué es {base}")
            continue

        # cost no lleva la comisión, y Kraken la apunta siempre en EUR o USD.
        compra = lado == "buy"
        operaciones.append(
            Operacion(
                cuando=cuando.replace(tzinfo=timezone.utc),
                coin_id=coin_id,
                tipo="compra" if compra else "venta",
                cantidad=cantidad,
                coste=importe + comision if compra else importe - comision,
                comision=comision or None,
                origen="Kraken",
            )
        )

    operaciones.sort(key=lambda o: o.cuando)
    return Lectura(operaciones, saltadas, 0, "Kraken")
