"""/cme: el hueco que dejan los futuros del CME entre el viernes y el domingo."""

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import requests

URL = "https://api.binance.com/api/v3/klines"
TIMEOUT = 15
# Mil horas son seis fines de semana largos.
HORAS = 1000
HORA = timedelta(hours=1)
# Los que siguen abiertos y salen en la lista, de los más cercanos al precio.
PENDIENTES = 3


class CmeError(Exception):
    """No se pudo leer de Binance."""


@dataclass(frozen=True)
class Vela:
    cuando: datetime
    apertura: float
    maximo: float
    minimo: float
    cierre: float


@dataclass(frozen=True)
class Hueco:
    viernes: datetime  # cuando cerró el CME
    antes: float  # el precio al cerrar
    domingo: datetime  # cuando volvió a abrir
    despues: float  # el precio al abrir
    cerrado: datetime | None  # la hora en que volvió al precio del viernes

    @property
    def tamaño(self) -> float:
        return (self.despues / self.antes - 1) * 100

    @property
    def horas(self) -> float | None:
        if self.cerrado is None:
            return None
        return (self.cerrado - self.domingo) / HORA


@dataclass(frozen=True)
class Cme:
    huecos: list[Hueco]  # del más viejo al último
    precio: float  # el de ahora
    # Si ahora es fin de semana y el CME está parado: cuándo cerró y a cuánto.
    parado: tuple[datetime, float] | None

    @property
    def ultimo(self) -> Hueco | None:
        return self.huecos[-1] if self.huecos else None

    @property
    def pendientes(self) -> list[Hueco]:
        """Los de antes que siguen sin cerrar, los más cerca del precio primero."""
        abiertos = [h for h in self.huecos[:-1] if h.cerrado is None]
        return sorted(abiertos, key=lambda h: abs(h.antes - self.precio))[:PENDIENTES]

    @property
    def cerrados(self) -> list[Hueco]:
        return [h for h in self.huecos if h.cerrado is not None]


def horario_de_verano(dia: date) -> bool:
    """El de Estados Unidos: del segundo domingo de marzo al primero de noviembre."""
    marzo = date(dia.year, 3, 8)
    noviembre = date(dia.year, 11, 1)
    empieza = marzo + timedelta(days=(6 - marzo.weekday()) % 7)
    acaba = noviembre + timedelta(days=(6 - noviembre.weekday()) % 7)
    return empieza <= dia < acaba


def cierre(viernes: date) -> datetime:
    """Las 17:00 de Nueva York, pasadas a UTC."""
    hora = 21 if horario_de_verano(viernes) else 22
    return datetime(viernes.year, viernes.month, viernes.day, hora, tzinfo=timezone.utc)


def apertura(domingo: date) -> datetime:
    hora = 22 if horario_de_verano(domingo) else 23
    return datetime(domingo.year, domingo.month, domingo.day, hora, tzinfo=timezone.utc)


def pedir() -> list:
    try:
        respuesta = requests.get(
            URL,
            params={"symbol": "BTCUSDT", "interval": "1h", "limit": HORAS},
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        raise CmeError(f"Binance no contesta: {e}") from e
    if respuesta.status_code == 451:
        raise CmeError("Binance no deja mirarlo desde este país")
    try:
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.RequestException as e:
        raise CmeError(f"Binance no contesta: {e}") from e
    except ValueError as e:
        raise CmeError("Binance devolvió algo que no es JSON") from e


def _velas(datos) -> dict[datetime, Vela]:
    velas = {}
    for v in datos if isinstance(datos, list) else []:
        try:
            cuando = datetime.fromtimestamp(int(v[0]) / 1000, timezone.utc)
            precios = [float(v[i]) for i in (1, 2, 3, 4)]
        except (TypeError, ValueError, IndexError, OverflowError, OSError):
            continue
        if all(p > 0 and math.isfinite(p) for p in precios):
            velas[cuando] = Vela(cuando, *precios)
    return velas


def leer(datos, ahora: datetime) -> Cme | None:
    """None si Binance no ha dado ni una vela."""
    velas = _velas(datos)
    if not velas:
        return None
    orden = sorted(velas)
    precio = velas[orden[-1]].cierre

    huecos = []
    parado = None
    viernes = orden[0].date() + timedelta(days=(4 - orden[0].weekday()) % 7)
    while viernes <= orden[-1].date():
        cerro, abrio = cierre(viernes), apertura(viernes + timedelta(days=2))
        antes = velas.get(cerro - HORA)
        if antes is not None and abrio in velas:
            despues = velas[abrio].apertura
            huecos.append(
                Hueco(
                    cerro, antes.cierre, abrio, despues, _cerrado(velas, abrio, antes)
                )
            )
        elif antes is not None and cerro <= ahora < abrio:
            parado = (cerro, antes.cierre)
        viernes += timedelta(days=7)
    return Cme(huecos, precio, parado)


def _cerrado(
    velas: dict[datetime, Vela], abrio: datetime, antes: Vela
) -> datetime | None:
    """La primera hora, desde que abre, en que el precio pasa por el del viernes."""
    for cuando in sorted(c for c in velas if c >= abrio):
        v = velas[cuando]
        if v.minimo <= antes.cierre <= v.maximo:
            return cuando
    return None
