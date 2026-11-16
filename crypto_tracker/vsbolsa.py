"""/vsbolsa: tu cartera contra haber metido lo mismo en un indexado, los mismos días."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import requests

from .movimientos import Movimiento
from .vsbtc import cantidades

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
# Sin un User-Agent de navegador, Yahoo contesta 429 a todo.
CABECERAS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 20

# ETF de acumulación: reinvierten los dividendos, que si no la bolsa sale perdiendo.
INDICES = {
    "sp500": ("S&P 500", {"eur": "SXR8.DE", "usd": "CSPX.L"}),
    "world": ("MSCI World", {"eur": "EUNL.DE", "usd": "IWDA.L"}),
}
NOMBRES = {
    "": "sp500",
    "sp500": "sp500",
    "sp": "sp500",
    "s&p": "sp500",
    "spx": "sp500",
    "world": "world",
    "msci": "world",
    "mundo": "world",
}

# La bolsa cierra los fines de semana y en fiestas: una compra de sábado va con
# el cierre del viernes. Más hueco que esto ya es que falta el dato.
MARGEN = timedelta(days=5)


class BolsaError(Exception):
    """No se pudo leer el precio del índice."""


@dataclass(frozen=True)
class Contra:
    indice: str  # el nombre, para el mensaje
    ticker: str
    real: float  # lo que vale hoy lo que compraste y aún tienes
    bolsa: float  # lo que valdría si todo hubiera ido al índice
    contados: int
    fuera: int  # sin precio o sin cierre de la bolsa de ese día
    desde: datetime

    @property
    def diferencia(self) -> float:
        return self.real - self.bolsa

    @property
    def ventaja(self) -> float | None:
        if self.bolsa <= 0:
            return None
        return (self.real / self.bolsa - 1) * 100


def interpretar(argumento: str, currency: str) -> tuple[str, str]:
    """'world' -> ('MSCI World', 'EUNL.DE'). A secas, el S&P 500."""
    clave = NOMBRES.get(argumento.strip().lower())
    if clave is None:
        raise BolsaError(
            "Puedo compararla con el S&P 500 o el MSCI World: /vsbolsa o /vsbolsa world"
        )
    nombre, tickers = INDICES[clave]
    ticker = tickers.get(currency.lower())
    if ticker is None:
        raise BolsaError("Solo sé compararla en euros o en dólares.")
    return nombre, ticker


def pedir(ticker: str, desde: datetime) -> tuple[list[tuple[date, float]], float]:
    """Los cierres desde esa fecha, del más viejo al más nuevo, y el precio de ahora."""
    params = {
        "period1": int(desde.timestamp()),
        "period2": int(datetime.now(timezone.utc).timestamp()),
        "interval": "1d",
    }
    try:
        respuesta = requests.get(
            URL.format(ticker), params=params, headers=CABECERAS, timeout=TIMEOUT
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
    except requests.RequestException as e:
        raise BolsaError(f"Yahoo no contesta: {e}") from e
    except ValueError as e:
        raise BolsaError("Yahoo devolvió algo que no es JSON") from e

    serie, ahora = leer(datos)
    if not serie or ahora is None:
        raise BolsaError("Yahoo no ha dado los precios del índice")
    return serie, ahora


def leer(datos) -> tuple[list[tuple[date, float]], float | None]:
    try:
        r = datos["chart"]["result"][0]
        marcas = r["timestamp"]
        cierres = r["indicators"]["quote"][0]["close"]
        ahora = r["meta"].get("regularMarketPrice")
    except (KeyError, IndexError, TypeError):
        return [], None

    serie = []
    # Algún día viene sin cierre, sobre todo el de hoy si la bolsa está abierta.
    for marca, cierre in zip(marcas, cierres, strict=False):
        if isinstance(cierre, int | float) and cierre > 0:
            dia = datetime.fromtimestamp(marca, timezone.utc).date()
            serie.append((dia, float(cierre)))
    if not isinstance(ahora, int | float) or ahora <= 0:
        ahora = serie[-1][1] if serie else None
    return serie, ahora


def precio_en(serie: list[tuple[date, float]], cuando: datetime) -> float | None:
    """El último cierre de ese día o de antes, si no queda muy lejos."""
    dia = cuando.date()
    antes = [(d, p) for d, p in serie if d <= dia]
    if not antes or dia - antes[-1][0] > MARGEN:
        return None
    return antes[-1][1]


def calcular(
    lista: list[Movimiento],
    serie: list[tuple[date, float]],
    ahora: float,
    precios: dict[str, float],
    indice: tuple[str, str],
) -> Contra | None:
    """None si no hay nada que comparar o falta el precio de hoy de alguna."""
    contables = []
    for m in sorted(lista, key=lambda m: m.id):
        precio = precio_en(serie, m.cuando)
        if m.coste is not None and precio:
            contables.append((m, precio))
    if not any(m.tipo != "recompensa" for m, _ in contables):
        return None

    participaciones = 0.0
    for m, precio in contables:
        # Un staking o un airdrop no los da la bolsa: suman en lo real y aquí no.
        if m.tipo == "recompensa":
            continue
        signo = 1 if m.tipo == "compra" else -1
        participaciones += signo * m.coste / precio
    participaciones = max(participaciones, 0.0)

    tienes = cantidades(contables)
    if any(c not in precios for c in tienes):
        return None

    return Contra(
        indice=indice[0],
        ticker=indice[1],
        real=sum(q * precios[c] for c, q in tienes.items()),
        bolsa=participaciones * ahora,
        contados=len(contables),
        fuera=len(lista) - len(contables),
        desde=contables[0][0].cuando,
    )
