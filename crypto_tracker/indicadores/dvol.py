"""/dvol: lo que las opciones de Deribit esperan que se mueva bitcoin."""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests

URL = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
TIMEOUT = 15
DIAS = 365
# Deribit solo tiene índice de estas dos.
MONEDAS = {"bitcoin": "BTC", "ethereum": "ETH"}

# Por lo que ha estado en el año y no por la cifra: ethereum siempre va más alto
# que bitcoin, y con los mismos cortes saldría nervioso todo el rato.
ZONAS = (
    (20, "😴", "Muy tranquilo para lo que suele: esperan poco movimiento"),
    (60, "😐", "Normal"),
    (90, "😬", "Nervioso: esperan más movimiento de lo normal"),
    (float("inf"), "🌪️", "De lo más alto del año: esperan movimientos muy fuertes"),
)


class DvolError(Exception):
    """No se pudo leer de Deribit."""


@dataclass(frozen=True)
class Dia:
    cuando: datetime
    valor: float


@dataclass(frozen=True)
class Dvol:
    moneda: str
    dias: list[Dia]  # del más viejo a hoy

    @property
    def hoy(self) -> Dia:
        return self.dias[-1]

    @property
    def hace_semana(self) -> Dia | None:
        return self.dias[-8] if len(self.dias) > 7 else None

    @property
    def por_debajo(self) -> float:
        """% de los días que estuvo más bajo que hoy."""
        return 100 * sum(d.valor < self.hoy.valor for d in self.dias) / len(self.dias)

    @property
    def maximo(self) -> Dia:
        return max(self.dias, key=lambda d: d.valor)

    @property
    def minimo(self) -> Dia:
        return min(self.dias, key=lambda d: d.valor)

    @property
    def zona(self) -> tuple[str, str]:
        return next((e, t) for tope, e, t in ZONAS if self.por_debajo < tope)

    def esperado(self, dias: int) -> float:
        """% que esperan que se mueva en esos días, arriba o abajo."""
        # Es anual: se escala con la raíz del tiempo, y cripto cotiza los 365.
        return self.hoy.valor * math.sqrt(dias / 365)


def pedir(moneda: str, ahora: datetime | None = None) -> list:
    ahora = ahora or datetime.now(timezone.utc)
    params = {
        "currency": moneda,
        "start_timestamp": int((ahora - timedelta(days=DIAS)).timestamp() * 1000),
        "end_timestamp": int(ahora.timestamp() * 1000),
        "resolution": "1D",
    }
    try:
        respuesta = requests.get(URL, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise DvolError(f"Deribit no contesta: {e}") from e
    try:
        respuesta.raise_for_status()
        datos = respuesta.json()
    except requests.RequestException as e:
        raise DvolError(f"Deribit no contesta: {e}") from e
    except ValueError as e:
        raise DvolError("Deribit devolvió algo que no es JSON") from e
    resultado = datos.get("result") if isinstance(datos, dict) else None
    return resultado.get("data") or [] if isinstance(resultado, dict) else []


def leer(moneda: str, datos) -> Dvol | None:
    """None si no hay ni un día que valga."""
    valores = {}
    for d in datos if isinstance(datos, list) else []:
        try:
            cuando = datetime.fromtimestamp(int(d[0]) / 1000, timezone.utc)
            valor = float(d[4])
        except (TypeError, ValueError, IndexError, OverflowError, OSError):
            continue
        if valor > 0 and math.isfinite(valor):
            valores[cuando] = valor
    if not valores:
        return None
    return Dvol(moneda, [Dia(c, valores[c]) for c in sorted(valores)])
