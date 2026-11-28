"""/funding: lo que se pagan los de los futuros de Binance entre ellos."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean

import requests

from ..nucleo.simbolos import de_id

AHORA_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
ANTES_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
TIMEOUT = 15

# Se paga cada 8 horas: 3 al día, 21 a la semana.
AL_DIA = 3
SEMANA = 21

# En %, por cada pago. Binance parte de 0,01% cuando no pasa nada.
NIVELES = [
    (
        -0.01,
        "😱",
        "Muchos apostando a que baja",
        "Cuando se pasan, a veces rebota de golpe",
    ),
    # Un poco por debajo de cero es ruido, no gente apostando a la baja.
    (-0.003, "🐻", "Algo más a la baja que al alza", ""),
    (0.015, "😐", "Tranquilo", "Ni muy al alza ni muy a la baja"),
    (0.05, "🐂", "Apostando a que sube", "Normal en una subida"),
    (
        float("inf"),
        "🔥",
        "Muy apalancado al alza",
        "Así suelen venir las caídas bruscas: cuando baja un poco, se cierran "
        "a la fuerza y lo empujan más",
    ),
]


EJEMPLO_AVISO = "/funding btc avisa"
AVISA = "avisa"
QUITAR = "quitar"
_AVISA = frozenset({"avisa", "aviso", "avisame", "avísame"})
_QUITAR = frozenset({"no", "quitar", "off"})

# La media de la semana se mueve cada 8 h, con cada pago: mirarla en cada
# ciclo sería preguntar a Binance cien veces por lo mismo.
CADA = timedelta(hours=1)

ALTO, BAJO = "alto", "bajo"


class FundingError(Exception):
    """No se pudo leer de Binance."""


@dataclass(frozen=True)
class Funding:
    par: str
    ahora: float  # % del último pago
    semana: float | None  # media de los últimos 21, en %
    emoji: str
    nivel: str
    que_pasa: str

    @property
    def al_año(self) -> float:
        tasa = self.ahora if self.semana is None else self.semana
        return tasa * AL_DIA * 365


@dataclass(frozen=True)
class Vigilado:
    """Uno de /funding btc avisa."""

    par: str
    coin_id: str
    extremo: str = ""  # ALTO o BAJO si ya se avisó de que está ahí; "" si no
    mirado: datetime | None = None  # la última vez que se preguntó a Binance


def separar(argumento: str) -> tuple[str, str | None]:
    """'btc avisa' -> ('btc', AVISA). 'btc no' -> ('btc', QUITAR). Si no, None."""
    partes = argumento.split()
    if len(partes) >= 2 and partes[-1].lower() in _AVISA:
        return " ".join(partes[:-1]), AVISA
    if len(partes) >= 2 and partes[-1].lower() in _QUITAR:
        return " ".join(partes[:-1]), QUITAR
    return argumento, None


def extremo(f: Funding) -> str:
    """ALTO o BAJO si está en uno de los dos niveles de las puntas; si no, ''."""
    tasa = f.ahora if f.semana is None else f.semana
    if tasa < NIVELES[0][0]:
        return BAJO
    if tasa >= NIVELES[-2][0]:
        return ALTO
    return ""


def toca_mirar(v: Vigilado, ahora: datetime) -> bool:
    return v.mirado is None or ahora - v.mirado >= CADA


def toca(v: Vigilado, f: Funding) -> tuple[bool, str]:
    """(toca avisar, dónde queda). Avisa al entrar en una punta, no mientras sigue."""
    donde = extremo(f)
    return bool(donde) and donde != v.extremo, donde


def par(coin_id: str, escrito: str = "") -> str:
    """'bitcoin' -> 'BTCUSDT'. Si no es de las conocidas, lo que escribiste."""
    simbolo = de_id(coin_id) or escrito.strip() or coin_id
    return f"{simbolo.upper()}USDT"


def pedir(par_: str) -> tuple[dict, list]:
    ahora = _get(AHORA_URL, {"symbol": par_})
    try:
        antes = _get(ANTES_URL, {"symbol": par_, "limit": SEMANA})
    except FundingError:
        antes = []
    return ahora, antes


def _get(url: str, params: dict):
    try:
        respuesta = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise FundingError(f"Binance no contesta: {e}") from e
    # Con un par que no existe contesta 400 y un -1121; es lo único que se
    # distingue, porque casi siempre es que no tiene futuros.
    if respuesta.status_code == 400:
        raise FundingError("sin futuros")
    if respuesta.status_code == 451:
        raise FundingError("Binance no deja mirarlo desde este país")
    try:
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.RequestException as e:
        raise FundingError(f"Binance no contesta: {e}") from e
    except ValueError as e:
        raise FundingError("Binance devolvió algo que no es JSON") from e


def _pct(valor) -> float | None:
    # Vienen como texto y en tanto por uno: "0.00010000" es un 0,01%.
    try:
        return float(valor) * 100
    except (TypeError, ValueError):
        return None


def leer(par_: str, ahora, antes) -> Funding | None:
    datos = ahora if isinstance(ahora, dict) else {}
    tasa = _pct(datos.get("lastFundingRate"))
    if tasa is None:
        return None

    pagos = [
        p
        for f in (antes if isinstance(antes, list) else [])
        if isinstance(f, dict) and (p := _pct(f.get("fundingRate"))) is not None
    ]
    semana = mean(pagos) if pagos else None
    # Por la media de la semana si la hay: un pago suelto engaña mucho.
    emoji, nivel, que_pasa = como_esta(tasa if semana is None else semana)
    return Funding(par_, tasa, semana, emoji, nivel, que_pasa)


def como_esta(tasa: float) -> tuple[str, str, str]:
    return next((e, n, q) for hasta, e, n, q in NIVELES if tasa < hasta)
