"""Lee la configuracion del .env y la valida al arrancar."""

import os
from dataclasses import dataclass

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
class Config:
    telegram_token: str
    telegram_chat_id: str
    watchlist: list[Watch]
    vs_currency: str
    check_interval: int
    database_path: str
    history_days: int


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
    """Convierte '30m', '2h' o '1d' en minutos. Sin letra se entienden horas."""
    raw = raw.strip().lower()
    if not raw:
        raise ConfigError("Falta el tiempo. Ejemplos: 30m, 2h, 1d.")

    unidades = {"m": 1, "h": 60, "d": 1440}
    factor = unidades.get(raw[-1])
    numero = raw[:-1] if factor else raw

    try:
        cantidad = float(numero)
    except ValueError:
        raise ConfigError(
            f"No entiendo '{raw}'. Usa algo como 30m, 2h o 1d."
        ) from None

    if cantidad <= 0:
        raise ConfigError(f"El tiempo tiene que ser mayor que 0, no '{raw}'.")

    minutos = int(cantidad * (factor or 60))
    if minutos < 1:
        raise ConfigError(f"'{raw}' es menos de un minuto.")

    return minutos


def load_config() -> Config:
    """Monta la configuracion. Lanza ConfigError si algo falta o esta mal."""
    return Config(
        telegram_token=_require("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_require("TELEGRAM_CHAT_ID"),
        watchlist=_parse_watchlist(_require("WATCHLIST")),
        vs_currency=os.getenv("VS_CURRENCY", "eur").strip().lower() or "eur",
        check_interval=_parse_positive_int("CHECK_INTERVAL", "300"),
        database_path=os.getenv("DATABASE_PATH", "data/prices.db").strip()
        or "data/prices.db",
        history_days=_parse_history_days(),
    )
