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
    """

    coin_id: str
    min_price: float | None = None
    max_price: float | None = None
    step: float | None = None


@dataclass(frozen=True)
class Config:
    telegram_token: str
    telegram_chat_id: str
    watchlist: list[Watch]
    vs_currency: str
    check_interval: int
    database_path: str


def _require(name: str) -> str:
    """Saca una variable obligatoria o revienta con un mensaje claro."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"Falta {name}. Copia .env.example a .env y rellenalo."
        )
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

    Admite dos formatos, mezclables en la misma lista:
      bitcoin:1000              -> avisa al cruzar 62000, 63000, 64000...
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
            watches.append(Watch(coin_id, step=_parse_step(parts[1], coin_id)))
            continue

        min_price = _parse_threshold(parts[1], coin_id, "minimo")
        max_price = _parse_threshold(parts[2], coin_id, "maximo")

        if min_price is None and max_price is None:
            raise ConfigError(
                f"'{coin_id}' no tiene ningun umbral, nunca avisaria."
            )

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
    )
