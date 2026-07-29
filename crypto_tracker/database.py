"""Guarda el historico de precios en SQLite."""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Guardamos la hora en UTC para que el historico no de saltos raros
# con los cambios de hora de verano.
SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    coin_id    TEXT    NOT NULL,
    price      REAL    NOT NULL,
    currency   TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_prices_coin_fecha
    ON prices (coin_id, created_at DESC);
"""


class DatabaseError(Exception):
    """Algo fallo al hablar con SQLite."""


@contextmanager
def _connect(db_path: str):
    """Abre la conexion, hace commit si va bien y la cierra siempre."""
    try:
        conn = sqlite3.connect(db_path)
        # Devuelve filas tipo dict (row["price"]) en vez de tuplas.
        conn.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        raise DatabaseError(f"No se pudo abrir la base de datos: {e}") from e

    try:
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise DatabaseError(f"Error en la base de datos: {e}") from e
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    """Crea el archivo y la tabla si no existen. Se puede llamar siempre."""
    # Si DATABASE_PATH apunta a data/prices.db, hay que crear data/ antes.
    parent = Path(db_path).parent
    if parent and not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise DatabaseError(f"No se pudo crear la carpeta {parent}: {e}") from e

    with _connect(db_path) as conn:
        conn.executescript(SCHEMA)

    logger.debug("Base de datos lista en %s", db_path)


def save_prices(db_path: str, prices: dict[str, float], currency: str) -> int:
    """Guarda una tanda de precios. Devuelve cuantas filas metio."""
    if not prices:
        return 0

    # Misma marca de tiempo para toda la tanda: son de la misma consulta.
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    filas = [(coin_id, precio, currency, ahora) for coin_id, precio in prices.items()]

    with _connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO prices (coin_id, price, currency, created_at) "
            "VALUES (?, ?, ?, ?)",
            filas,
        )

    logger.debug("Guardados %d precios", len(filas))
    return len(filas)


def get_last_price(db_path: str, coin_id: str) -> float | None:
    """Ultimo precio guardado de una cripto, o None si no hay ninguno."""
    with _connect(db_path) as conn:
        fila = conn.execute(
            "SELECT price FROM prices WHERE coin_id = ? "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (coin_id,),
        ).fetchone()

    return fila["price"] if fila else None


def get_history(db_path: str, coin_id: str, limit: int = 50) -> list[sqlite3.Row]:
    """Historico de una cripto, del mas reciente al mas antiguo."""
    with _connect(db_path) as conn:
        return conn.execute(
            "SELECT coin_id, price, currency, created_at FROM prices "
            "WHERE coin_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (coin_id, limit),
        ).fetchall()
