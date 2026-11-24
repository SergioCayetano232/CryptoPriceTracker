"""/kimchi: lo que se paga de más por bitcoin en Corea, en Upbit, frente a Binance."""

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import requests

UPBIT_URL = "https://api.upbit.com/v1/candles/days"
BINANCE_URL = "https://api.binance.com/api/v3/klines"
# Los cambios del BCE, gratis y sin clave. No da fines de semana ni festivos.
CAMBIO_URL = "https://api.frankfurter.dev/v1/{desde}.."
TIMEOUT = 15
DIAS = 30

EUFORIA = 5.0
GANAS = 2.0
DESCUENTO = -1.0

EJEMPLO = "/kimchi btc"


class KimchiError(Exception):
    """No se pudo leer de Upbit, Binance o el cambio del won."""


@dataclass(frozen=True)
class Dia:
    dia: date
    prima: float  # % que vale de más en Corea


@dataclass(frozen=True)
class Kimchi:
    simbolo: str
    wones: float  # precio de hoy en Upbit
    dolares: float  # lo mismo en Binance
    cambio: float  # wones por dólar
    dias: list[Dia]  # del más viejo a hoy

    @property
    def ahora(self) -> float:
        return self.dias[-1].prima

    @property
    def media(self) -> float:
        return sum(d.prima for d in self.dias) / len(self.dias)

    @property
    def nivel(self) -> str:
        if self.ahora >= EUFORIA:
            return "euforia"
        if self.ahora >= GANAS:
            return "ganas"
        return "descuento" if self.ahora <= DESCUENTO else ""


def pedir(simbolo: str, hoy: date) -> tuple[list, list, dict]:
    upbit = _get(UPBIT_URL, {"market": f"KRW-{simbolo}", "count": DIAS})
    binance = _get(
        BINANCE_URL, {"symbol": f"{simbolo}USDT", "interval": "1d", "limit": DIAS}
    )
    # Unos días antes, para tener el cambio del viernes si el primero es domingo.
    desde = hoy - timedelta(days=DIAS + 5)
    cambio = _get(
        CAMBIO_URL.format(desde=desde.isoformat()), {"base": "USD", "symbols": "KRW"}
    )
    return upbit, binance, cambio


def _get(url: str, params: dict):
    quien = "Upbit" if "upbit" in url else "Binance" if "binance" in url else "El BCE"
    try:
        respuesta = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise KimchiError(f"{quien} no contesta: {e}") from e
    # Upbit da 404 con una que no tiene; Binance, 400.
    if respuesta.status_code in (400, 404) and quien != "El BCE":
        raise KimchiError("sin datos")
    if respuesta.status_code == 451:
        raise KimchiError("Binance no deja mirarlo desde este país")
    try:
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.RequestException as e:
        raise KimchiError(f"{quien} no contesta: {e}") from e
    except ValueError as e:
        raise KimchiError(f"{quien} devolvió algo que no es JSON") from e


def _positivo(valor) -> float | None:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if numero > 0 and math.isfinite(numero) else None


def _upbit(velas) -> dict[date, float]:
    dias = {}
    for v in velas if isinstance(velas, list) else []:
        if not isinstance(v, dict):
            continue
        precio = _positivo(v.get("trade_price"))
        try:
            dia = date.fromisoformat(str(v.get("candle_date_time_utc"))[:10])
        except ValueError:
            continue
        if precio:
            dias[dia] = precio
    return dias


def _binance(velas) -> dict[date, float]:
    dias = {}
    for v in velas if isinstance(velas, list) else []:
        try:
            dia = datetime.fromtimestamp(int(v[0]) / 1000, timezone.utc).date()
            precio = _positivo(v[4])
        except (TypeError, ValueError, IndexError, OverflowError, OSError):
            continue
        if precio:
            dias[dia] = precio
    return dias


def _cambios(datos) -> dict[date, float]:
    tasas = datos.get("rates") if isinstance(datos, dict) else None
    dias = {}
    for texto, monedas in (tasas if isinstance(tasas, dict) else {}).items():
        try:
            dia = date.fromisoformat(texto)
        except ValueError:
            continue
        valor = _positivo(monedas.get("KRW")) if isinstance(monedas, dict) else None
        if valor:
            dias[dia] = valor
    return dias


def leer(simbolo: str, upbit, binance, cambio) -> Kimchi | None:
    """None si no hay ni un día con los tres datos."""
    en_corea, fuera, tasas = _upbit(upbit), _binance(binance), _cambios(cambio)
    dias = []
    ultimo = None
    for dia in sorted(set(en_corea) & set(fuera)):
        # Fin de semana o festivo: vale el último cambio que hubo.
        anteriores = [d for d in tasas if d <= dia]
        if not anteriores:
            continue
        tasa = tasas[max(anteriores)]
        prima = (en_corea[dia] / (fuera[dia] * tasa) - 1) * 100
        dias.append(Dia(dia, prima))
        ultimo = (en_corea[dia], fuera[dia], tasa)
    if ultimo is None:
        return None
    return Kimchi(simbolo, *ultimo, dias)
