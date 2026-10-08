"""Lee la configuracion del .env y la valida al arrancar."""

import math
import os
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from dotenv import load_dotenv

# Carga el .env en las variables de entorno. Si no existe no pasa nada,
# se usaran las variables del sistema (util para Docker o servidores).
load_dotenv()


class ConfigError(Exception):
    """Falta algo en el .env o esta mal escrito."""


@dataclass(frozen=True)
class Watch:
    """Una cripto vigilada. Cada tipo de aviso es opcional (None = no vigilar).

    min_price/max_price avisan al cruzar un precio fijo.
    step avisa al cruzar cualquier multiplo de ese valor.
    percent avisa cuando el precio se mueve ese porcentaje.
    """

    coin_id: str
    min_price: float | None = None
    max_price: float | None = None
    step: float | None = None
    percent: float | None = None


@dataclass(frozen=True)
class Posicion:
    """Lo que tienes de una cripto. invertido es opcional, lo que te costo."""

    coin_id: str
    cantidad: float
    invertido: float | None = None


@dataclass(frozen=True)
class Config:
    telegram_token: str
    telegram_chat_id: str
    watchlist: list[Watch]
    vs_currency: str
    check_interval: int
    database_path: str
    history_days: int
    # None = sin resumen diario
    resumen_diario: time | None = None
    # None = sin aviso de movimientos bruscos
    brusco_porcentaje: float | None = None
    brusco_minutos: int = 60
    # (inicio, fin), o None si no hay horas tranquilas
    horas_tranquilas: tuple[time, time] | None = None
    cartera: tuple[Posicion, ...] = ()
    # None = sin aviso de maximos y minimos
    extremos_dias: int | None = None


def _require(name: str) -> str:
    """Saca una variable obligatoria o revienta con un mensaje claro."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Falta {name}. Copia .env.example a .env y rellenalo.")
    return value


def _parse_threshold(raw: str, coin_id: str, label: str) -> float | None:
    """Convierte un umbral a float. Vacio significa 'no vigilar este lado'."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        raise ConfigError(
            f"El umbral {label} de '{coin_id}' no es un numero: '{raw}'"
        ) from None


def _parse_watchlist(raw: str) -> list[Watch]:
    """Convierte el texto de WATCHLIST en objetos Watch.

    Admite tres formatos, mezclables en la misma lista:
      bitcoin:1000              -> avisa al cruzar 62000, 63000, 64000...
      bitcoin:%5                -> avisa cuando se mueve un 5%
      bitcoin:55000:75000       -> avisa al cruzar esos precios
    """
    watches = []

    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue

        parts = entry.split(":")
        if len(parts) not in (2, 3):
            raise ConfigError(
                f"Formato malo en WATCHLIST: '{entry}'. Se espera id:paso "
                "(ej: bitcoin:1000) o id:minimo:maximo (ej: bitcoin:55000:75000)."
            )

        coin_id = parts[0].strip().lower()
        if not coin_id:
            raise ConfigError(f"Falta el id de la cripto en: '{entry}'")

        # El estado se guarda por cripto: con dos entradas se pisarian una a
        # otra y ninguna avisaria bien.
        if coin_id in {w.coin_id for w in watches}:
            raise ConfigError(
                f"'{coin_id}' esta dos veces en WATCHLIST. Deja solo una forma "
                "de vigilarla."
            )

        if len(parts) == 2:
            valor = parts[1].strip()
            if valor.startswith("%"):
                watches.append(
                    Watch(coin_id, percent=_parse_percent(valor[1:], coin_id))
                )
            else:
                watches.append(Watch(coin_id, step=_parse_step(valor, coin_id)))
            continue

        min_price = _parse_threshold(parts[1], coin_id, "minimo")
        max_price = _parse_threshold(parts[2], coin_id, "maximo")

        if min_price is None and max_price is None:
            raise ConfigError(f"'{coin_id}' no tiene ningun umbral, nunca avisaria.")

        # Un minimo por encima del maximo dispararia las dos alertas a la vez.
        if min_price is not None and max_price is not None and min_price >= max_price:
            raise ConfigError(
                f"En '{coin_id}' el minimo ({min_price}) no puede ser "
                f"mayor o igual que el maximo ({max_price})."
            )

        watches.append(Watch(coin_id, min_price, max_price))

    if not watches:
        raise ConfigError("WATCHLIST esta vacia, no hay nada que vigilar.")

    return watches


def parse_entrada(raw: str) -> Watch:
    """Una sola entrada con el formato de WATCHLIST: 'solana:%5'."""
    if "," in raw:
        raise ConfigError(f"Solo una cripto cada vez, no '{raw}'")
    return _parse_watchlist(raw)[0]


def _parse_step(raw: str, coin_id: str) -> float:
    """Lee el paso de variacion. Tiene que ser un numero mayor que cero."""
    valor = _parse_threshold(raw, coin_id, "paso")

    if valor is None:
        raise ConfigError(f"Falta el paso de variacion de '{coin_id}'.")
    if valor <= 0:
        raise ConfigError(
            f"El paso de '{coin_id}' tiene que ser mayor que 0, no {valor}."
        )
    return valor


def _parse_percent(raw: str, coin_id: str) -> float:
    """Lee el porcentaje de variacion. Mayor que cero y menor que cien."""
    valor = _parse_threshold(raw, coin_id, "porcentaje")

    if valor is None:
        raise ConfigError(f"Falta el porcentaje de '{coin_id}' (ej: {coin_id}:%5).")
    if valor <= 0:
        raise ConfigError(
            f"El porcentaje de '{coin_id}' tiene que ser mayor que 0, no {valor}."
        )
    # Un 100% pide que doble o se vaya a cero: casi seguro es un dedazo.
    if valor >= 100:
        raise ConfigError(
            f"El porcentaje de '{coin_id}' ({valor}%) es demasiado grande, "
            "no avisaria casi nunca."
        )
    return valor


def _parse_positive_int(name: str, default: str) -> int:
    """Lee un entero que tiene que ser mayor que cero."""
    raw = os.getenv(name, default).strip() or default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{name} tiene que ser un numero entero: '{raw}'") from None

    if value <= 0:
        raise ConfigError(f"{name} tiene que ser mayor que 0, no {value}.")
    return value


def _parse_history_days() -> int:
    """Dias de historico que se guardan. 0 desactiva la purga."""
    raw = os.getenv("HISTORY_DAYS", "90").strip() or "90"
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(
            f"HISTORY_DAYS tiene que ser un numero entero: '{raw}'"
        ) from None

    if value < 0:
        raise ConfigError(
            f"HISTORY_DAYS no puede ser negativo ({value}). Usa 0 para no purgar."
        )
    return value


def parse_duracion(raw: str) -> int:
    """Convierte '30m', '2h', '1d' o '2sem' en minutos. Sin letra son horas."""
    raw = raw.strip().lower()
    if not raw:
        raise ConfigError("Falta el tiempo. Ejemplos: 30m, 2h, 1d.")

    # Semanas con "sem" y no con "s": /mute 30s callaria 30 semanas sin querer.
    unidades = {"sem": 10080, "w": 10080, "m": 1, "h": 60, "d": 1440}
    unidad = next((u for u in unidades if raw.endswith(u)), "")
    factor = unidades.get(unidad)
    numero = raw.removesuffix(unidad)

    try:
        cantidad = float(numero)
    except ValueError:
        raise ConfigError(f"No entiendo '{raw}'. Usa algo como 30m, 2h o 1d.") from None

    if cantidad <= 0:
        raise ConfigError(f"El tiempo tiene que ser mayor que 0, no '{raw}'.")

    minutos = int(cantidad * (factor or 60))
    if minutos < 1:
        raise ConfigError(f"'{raw}' es menos de un minuto.")

    return minutos


def minutos_mute(raw: str, ahora: datetime) -> int:
    """Lo que dura un mute: '2h' o 'hasta 8:00'. Si esa hora ya ha pasado, mañana."""
    raw = raw.strip().lower()
    # "8" a secas siguen siendo ocho horas, como siempre; la hora va con "hasta" o ":"
    if not raw.startswith("hasta") and ":" not in raw:
        return parse_duracion(raw)

    try:
        hora = parse_hora(raw.removeprefix("hasta").strip())
    except ConfigError:
        hora = None
    if hora is None:
        raise ConfigError(f"No entiendo '{raw}'. Usa algo como hasta 8:00.")

    # En hora de aqui y sin desfase fijo: la noche del cambio de hora, las 8:00
    # con el de verano serian las 7:00 de verdad.
    local = ahora.astimezone().replace(tzinfo=None)
    hasta = local.replace(hour=hora.hour, minute=hora.minute, second=0, microsecond=0)
    if hasta <= local:
        hasta += timedelta(days=1)
    # Hacia arriba: si no, con los segundos de ahora se quedaria en las 7:59
    return math.ceil((hasta.astimezone() - ahora).total_seconds() / 60)


def parse_hora(raw: str, nombre: str = "RESUMEN_DIARIO") -> time | None:
    """Convierte '09:00' o '9' en una hora. Vacio es None, sin resumen."""
    raw = raw.strip()
    if not raw:
        return None

    horas, _, minutos = raw.partition(":")
    try:
        return time(int(horas), int(minutos or 0))
    except ValueError:
        raise ConfigError(
            f"{nombre} tiene que ser una hora tipo 09:00, no '{raw}'"
        ) from None


def parse_tramo(raw: str) -> tuple[time, time] | None:
    """'23-8' o '23:30-7:00' -> (inicio, fin). Vacio es None."""
    raw = raw.strip()
    if not raw:
        return None

    inicio, guion, fin = raw.partition("-")
    if not guion or not inicio.strip() or not fin.strip():
        raise ConfigError(f"HORAS_TRANQUILAS tiene que ser algo como 23-8, no '{raw}'")

    tramo = (
        parse_hora(inicio, "HORAS_TRANQUILAS"),
        parse_hora(fin, "HORAS_TRANQUILAS"),
    )
    if tramo[0] == tramo[1]:
        raise ConfigError("HORAS_TRANQUILAS empieza y acaba a la misma hora.")
    return tramo


def parse_cartera(raw: str) -> tuple[Posicion, ...]:
    """'bitcoin:0.016:1000,ethereum:0.4' -> posiciones. Vacio, sin cartera."""
    posiciones = []

    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue

        parts = [x.strip() for x in entry.split(":")]
        if len(parts) not in (2, 3) or not parts[0]:
            raise ConfigError(
                f"Formato malo en PORTFOLIO: '{entry}'. Se espera "
                "cripto:cantidad o cripto:cantidad:invertido (ej: bitcoin:0.016:1000)."
            )

        coin_id = parts[0].lower()
        if coin_id in {p.coin_id for p in posiciones}:
            raise ConfigError(f"'{coin_id}' esta dos veces en PORTFOLIO.")

        cantidad = _parse_threshold(parts[1], coin_id, "cantidad")
        if cantidad is None or cantidad <= 0:
            raise ConfigError(f"La cantidad de '{coin_id}' tiene que ser mayor que 0.")

        invertido = (
            _parse_threshold(parts[2], coin_id, "invertido")
            if len(parts) == 3
            else None
        )
        if invertido is not None and invertido < 0:
            raise ConfigError(f"Lo invertido en '{coin_id}' no puede ser negativo.")

        posiciones.append(Posicion(coin_id, cantidad, invertido))

    return tuple(posiciones)


def parse_brusco(raw: str) -> tuple[float, int] | None:
    """'8%/1h' -> (8.0, 60). Sin tiempo es una hora. Vacio es None."""
    raw = raw.strip()
    if not raw:
        return None

    texto_pct, _, tiempo = raw.partition("/")
    try:
        porcentaje = float(texto_pct.strip().strip("%"))
    except ValueError:
        raise ConfigError(
            f"MOVIMIENTO_BRUSCO tiene que ser algo como 8%/1h, no '{raw}'"
        ) from None

    if not 0 < porcentaje < 100:
        raise ConfigError(
            f"El porcentaje de MOVIMIENTO_BRUSCO tiene que estar entre 0 y 100, "
            f"no {porcentaje}."
        )

    minutos = parse_duracion(tiempo) if tiempo.strip() else 60
    return porcentaje, minutos


def parse_extremos(raw: str) -> int | None:
    """'30d' -> 30. Vacio es None."""
    raw = raw.strip().lower()
    if not raw:
        return None

    try:
        dias = int(raw.removesuffix("d"))
    except ValueError:
        raise ConfigError(
            f"MAXIMOS_MINIMOS tiene que ser un numero de dias, como 30d, no '{raw}'"
        ) from None
    # Con un dia, cualquier subida de la tarde ya seria "maximo".
    if dias < 2:
        raise ConfigError("MAXIMOS_MINIMOS tiene que ser de 2 dias o mas.")
    return dias


def load_config() -> Config:
    """Monta la configuracion. Lanza ConfigError si algo falta o esta mal."""
    check_interval = _parse_positive_int("CHECK_INTERVAL", "300")
    brusco = parse_brusco(os.getenv("MOVIMIENTO_BRUSCO", ""))

    # Con una ventana mas corta que el intervalo nunca habria dos precios
    # que comparar y el aviso no saltaria jamas.
    if brusco and brusco[1] * 60 <= check_interval:
        raise ConfigError(
            f"La ventana de MOVIMIENTO_BRUSCO ({brusco[1]} min) tiene que ser "
            f"mas larga que CHECK_INTERVAL ({check_interval} s)."
        )

    history_days = _parse_history_days()
    extremos = parse_extremos(os.getenv("MAXIMOS_MINIMOS", ""))
    # Si se borra antes, nunca habria historico suficiente y no avisaria nunca.
    if extremos and history_days and extremos > history_days:
        raise ConfigError(
            f"MAXIMOS_MINIMOS ({extremos}d) mira mas atras de lo que guarda "
            f"HISTORY_DAYS ({history_days}). Sube HISTORY_DAYS o baja los dias."
        )

    return Config(
        telegram_token=_require("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_require("TELEGRAM_CHAT_ID"),
        watchlist=_parse_watchlist(_require("WATCHLIST")),
        vs_currency=os.getenv("VS_CURRENCY", "eur").strip().lower() or "eur",
        check_interval=check_interval,
        database_path=os.getenv("DATABASE_PATH", "data/prices.db").strip()
        or "data/prices.db",
        history_days=history_days,
        resumen_diario=parse_hora(os.getenv("RESUMEN_DIARIO", "")),
        brusco_porcentaje=brusco[0] if brusco else None,
        brusco_minutos=brusco[1] if brusco else 60,
        horas_tranquilas=parse_tramo(os.getenv("HORAS_TRANQUILAS", "")),
        cartera=parse_cartera(os.getenv("PORTFOLIO", "")),
        extremos_dias=extremos,
    )
