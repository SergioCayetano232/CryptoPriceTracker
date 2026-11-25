"""/maxpain: el precio al que más pierden los que compraron opciones del viernes."""

import math
from dataclasses import dataclass
from datetime import date, datetime, timezone

import requests

URL = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency"
TIMEOUT = 15
MONEDAS = {"bitcoin": "BTC", "ethereum": "ETH"}
MESES = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
]
# Deribit vence siempre a las 8:00 UTC.
HORA = 8


class MaxPainError(Exception):
    """No se pudo leer de Deribit."""


@dataclass(frozen=True)
class Opcion:
    vence: datetime
    strike: float
    call: bool
    abiertas: float  # en la moneda: una opción de BTC es un bitcoin


@dataclass(frozen=True)
class Vencimiento:
    moneda: str
    vence: datetime
    opciones: list[Opcion]
    precio: float  # el índice de ahora, en dólares

    @property
    def calls(self) -> float:
        return sum(o.abiertas for o in self.opciones if o.call)

    @property
    def puts(self) -> float:
        return sum(o.abiertas for o in self.opciones if not o.call)

    @property
    def abiertas(self) -> float:
        return self.calls + self.puts

    @property
    def put_call(self) -> float | None:
        return self.puts / self.calls if self.calls else None

    def pago(self, precio: float) -> float:
        """Lo que cobrarían en dólares los que compraron si vence a ese precio."""
        return sum(
            o.abiertas * max(0.0, precio - o.strike if o.call else o.strike - precio)
            for o in self.opciones
        )

    @property
    def max_pain(self) -> float:
        strikes = sorted({o.strike for o in self.opciones})
        return min(strikes, key=self.pago)

    def mas_abiertas(self, call: bool) -> float | None:
        """El strike con más abiertas de ese lado."""
        por_strike: dict[float, float] = {}
        for o in self.opciones:
            if o.call == call:
                por_strike[o.strike] = por_strike.get(o.strike, 0) + o.abiertas
        return max(por_strike, key=por_strike.get) if por_strike else None


@dataclass(frozen=True)
class MaxPain:
    viernes: Vencimiento
    gordo: Vencimiento  # el que más tiene abierto de los que quedan


def pedir(moneda: str) -> list:
    try:
        respuesta = requests.get(
            URL, params={"currency": moneda, "kind": "option"}, timeout=TIMEOUT
        )
    except requests.RequestException as e:
        raise MaxPainError(f"Deribit no contesta: {e}") from e
    try:
        respuesta.raise_for_status()
        datos = respuesta.json()
    except requests.RequestException as e:
        raise MaxPainError(f"Deribit no contesta: {e}") from e
    except ValueError as e:
        raise MaxPainError("Deribit devolvió algo que no es JSON") from e
    resultado = datos.get("result") if isinstance(datos, dict) else None
    return resultado if isinstance(resultado, list) else []


def vence(texto: str) -> datetime:
    """'27NOV26' -> el 27/11/2026 a las 8:00 UTC."""
    dia, mes, año = texto[:-5], texto[-5:-2], texto[-2:]
    fecha = date(2000 + int(año), MESES.index(mes) + 1, int(dia))
    return datetime(fecha.year, fecha.month, fecha.day, HORA, tzinfo=timezone.utc)


def _opcion(d: dict) -> tuple[Opcion, float] | None:
    """La opción y el precio del índice que trae, o None si algo no cuadra."""
    try:
        _, cuando, strike, lado = d["instrument_name"].split("-")
        opcion = Opcion(
            vence(cuando), float(strike), lado == "C", float(d["open_interest"])
        )
        precio = float(d["estimated_delivery_price"])
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    if lado not in ("C", "P") or not math.isfinite(precio) or precio <= 0:
        return None
    if opcion.abiertas < 0 or not math.isfinite(opcion.abiertas):
        return None
    return opcion, precio


def leer(moneda: str, datos, ahora: datetime) -> MaxPain | None:
    """None si no queda ningún vencimiento de viernes con opciones abiertas."""
    por_fecha: dict[datetime, list[Opcion]] = {}
    precio = None
    for d in datos if isinstance(datos, list) else []:
        leida = _opcion(d) if isinstance(d, dict) else None
        if leida is None:
            continue
        opcion, precio = leida
        if opcion.vence > ahora and opcion.abiertas > 0:
            por_fecha.setdefault(opcion.vence, []).append(opcion)
    if precio is None:
        return None

    vencimientos = [
        Vencimiento(moneda, v, o, precio) for v, o in sorted(por_fecha.items())
    ]
    # Los diarios son poca cosa: el que se mira es el de los viernes.
    viernes = next((v for v in vencimientos if v.vence.weekday() == 4), None)
    if viernes is None:
        return None
    return MaxPain(viernes, max(vencimientos, key=lambda v: v.abiertas))
