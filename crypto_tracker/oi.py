"""/oi: cuánto hay apostado en los futuros de Binance y si entra o sale."""

from dataclasses import dataclass
from datetime import datetime, timezone

# El mismo cliente que /funding: mismos errores, mismo 400 sin futuros.
from .funding import FundingError, _get

URL = "https://fapi.binance.com/futures/data/openInterestHist"
DIAS = 30

# Por debajo de esto, en una semana, es ruido.
MUCHO_OI = 5.0
MUCHO_PRECIO = 2.0

EJEMPLO = "/oi btc"

CON_GASOLINA = (
    "Entra dinero apostando a que sube. Tiene gasolina, y también más apalancamiento"
)
CIERRAN_CORTOS = (
    "Sube porque cierran los que apostaban a la baja, no porque entre dinero. "
    "Suele durar poco"
)


@dataclass(frozen=True)
class Dia:
    cuando: datetime
    contratos: float  # en la cripto: 93.000 BTC
    valor: float  # en dólares

    @property
    def precio(self) -> float:
        return self.valor / self.contratos


@dataclass(frozen=True)
class Interes:
    par: str
    dias: list[Dia]  # del más viejo al de hoy

    @property
    def hoy(self) -> Dia:
        return self.dias[-1]

    def cambio(self, dias: int) -> float | None:
        """% de contratos frente a hace tantos días. En contratos y no en dólares:
        si no, una subida del precio parecería dinero nuevo."""
        if len(self.dias) <= dias:
            return None
        return (self.hoy.contratos / self.dias[-1 - dias].contratos - 1) * 100

    def cambio_precio(self, dias: int) -> float | None:
        if len(self.dias) <= dias:
            return None
        return (self.hoy.precio / self.dias[-1 - dias].precio - 1) * 100

    @property
    def maximo(self) -> bool:
        return self.hoy.contratos >= max(d.contratos for d in self.dias)


def pedir(par: str) -> list:
    datos = _get(URL, {"symbol": par, "period": "1d", "limit": DIAS + 1})
    # Aquí, con un par que no existe, no da el 400 de /funding: da la lista vacía.
    if datos == []:
        raise FundingError("sin futuros")
    return datos


def _num(valor) -> float | None:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if numero > 0 else None


def leer(par: str, datos) -> Interes | None:
    """None si Binance no da al menos dos días que se puedan comparar."""
    dias = []
    for d in datos if isinstance(datos, list) else []:
        if not isinstance(d, dict) or not isinstance(d.get("timestamp"), int):
            continue
        contratos = _num(d.get("sumOpenInterest"))
        valor = _num(d.get("sumOpenInterestValue"))
        if contratos and valor:
            cuando = datetime.fromtimestamp(d["timestamp"] / 1000, timezone.utc)
            dias.append(Dia(cuando, contratos, valor))
    dias.sort(key=lambda d: d.cuando)
    return Interes(par, dias) if len(dias) >= 2 else None


def lectura(i: Interes) -> tuple[str, str]:
    """(emoji, qué pasa) con lo de la semana, o con lo que haya si es menos."""
    dias = min(7, len(i.dias) - 1)
    oi, precio = i.cambio(dias), i.cambio_precio(dias)
    if oi >= MUCHO_OI and precio >= MUCHO_PRECIO:
        return "🐂", CON_GASOLINA
    if oi >= MUCHO_OI and precio <= -MUCHO_PRECIO:
        return "🐻", "Se abren apuestas a que baja mientras cae"
    if oi >= MUCHO_OI:
        return (
            "⚡",
            "Entra dinero pero el precio no se mueve: se está cargando para un lado",
        )
    if oi <= -MUCHO_OI and precio >= MUCHO_PRECIO:
        return "🩳", CIERRAN_CORTOS
    if oi <= -MUCHO_OI and precio <= -MUCHO_PRECIO:
        return "🎈", "Se cierran posiciones mientras baja: se está desinflando"
    if oi <= -MUCHO_OI:
        return "🧹", "Se cierran apuestas: menos apalancamiento, más tranquilo"
    return "😐", "Sin cambios grandes en lo apostado"
