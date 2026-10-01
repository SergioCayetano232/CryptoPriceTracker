"""Guarda el historico de precios en SQLite."""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .puntuales import Puntual

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

-- Por donde iba cada cripto la ultima vez: la zona (bajo/normal/alto) si
-- vigila un rango, el ultimo nivel si va por pasos, o "%precio" si va por %.
-- Guardarlo aqui evita repetir el mismo aviso al reiniciar el programa.
CREATE TABLE IF NOT EXISTS alert_state (
    coin_id    TEXT PRIMARY KEY,
    estado     TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Ajustes sueltos, de momento solo hasta cuando estan silenciados los avisos.
-- Una tabla de clave/valor evita tener que migrar cada vez que anada algo.
CREATE TABLE IF NOT EXISTS ajustes (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

-- Las de /alerta: avisan una vez y se borran. sube = 1 si espera a que suba.
CREATE TABLE IF NOT EXISTS alertas_puntuales (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    coin_id    TEXT    NOT NULL,
    objetivo   REAL    NOT NULL,
    sube       INTEGER NOT NULL,
    currency   TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);

-- Lo que cambias por Telegram encima del WATCHLIST del .env. regla va con el
-- mismo formato (solana:%5.0), y NULL es que la dejaste. de_cero = 1 hasta
-- que un ciclo olvide por donde iba con la regla vieja.
CREATE TABLE IF NOT EXISTS watchlist_cambios (
    coin_id    TEXT PRIMARY KEY,
    regla      TEXT,
    de_cero    INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);
"""

# Clave donde se guarda hasta cuando callamos, en ISO y UTC.
SILENCIO = "silenciado_hasta"

# Dia del ultimo resumen diario, para no mandarlo dos veces si se reinicia.
ULTIMO_RESUMEN = "ultimo_resumen"


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


def purge_old_prices(db_path: str, dias: int) -> int:
    """Borra los precios mas viejos que `dias`. Devuelve cuantos borro."""
    if dias <= 0:
        return 0

    corte = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat(
        timespec="seconds"
    )

    with _connect(db_path) as conn:
        cursor = conn.execute("DELETE FROM prices WHERE created_at < ?", (corte,))
        borradas = cursor.rowcount

    if borradas > 0:
        logger.info("Purgados %d precios de mas de %d dias", borradas, dias)

    return borradas


def get_last_price(db_path: str, coin_id: str) -> float | None:
    """Ultimo precio guardado de una cripto, o None si no hay ninguno."""
    with _connect(db_path) as conn:
        fila = conn.execute(
            "SELECT price FROM prices WHERE coin_id = ? "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (coin_id,),
        ).fetchone()

    return fila["price"] if fila else None


def get_price_at(
    db_path: str, coin_id: str, horas: int, margen: int = 12
) -> float | None:
    """Precio guardado mas cercano a hace `horas`, mirando solo hacia atras.

    Solo vale si es de esa franja: `margen` horas antes como mucho. Si el
    bot ha estado parado una semana, lo mas reciente es de hace siete dias
    y llamar a eso "variacion en 24h" seria mentira. Mejor no decir nada.
    """
    ahora = datetime.now(timezone.utc)
    corte = (ahora - timedelta(hours=horas)).isoformat(timespec="seconds")
    limite = (ahora - timedelta(hours=horas + margen)).isoformat(timespec="seconds")

    with _connect(db_path) as conn:
        fila = conn.execute(
            "SELECT price FROM prices WHERE coin_id = ? "
            "AND created_at <= ? AND created_at >= ? "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (coin_id, corte, limite),
        ).fetchone()

    return fila["price"] if fila else None


def get_prices_since(
    db_path: str, coin_id: str, horas: int, currency: str
) -> list[float]:
    """Precios de las ultimas `horas`, del mas viejo al mas nuevo."""
    desde = datetime.now(timezone.utc) - timedelta(hours=horas)
    return get_prices_desde(db_path, coin_id, desde, currency)


def get_serie(
    db_path: str, coin_id: str, horas: int, currency: str
) -> list[tuple[datetime, float]]:
    """Como get_prices_since, pero con la hora de cada precio, para dibujarlo."""
    desde = (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat(
        timespec="seconds"
    )

    with _connect(db_path) as conn:
        filas = conn.execute(
            "SELECT created_at, price FROM prices WHERE coin_id = ? AND currency = ? "
            "AND created_at >= ? ORDER BY created_at, id",
            (coin_id, currency, desde),
        ).fetchall()

    return [(datetime.fromisoformat(f["created_at"]), f["price"]) for f in filas]


def get_prices_desde(
    db_path: str, coin_id: str, desde: datetime, currency: str
) -> list[float]:
    """Precios guardados a partir de `desde`, del mas viejo al mas nuevo."""
    with _connect(db_path) as conn:
        filas = conn.execute(
            "SELECT price FROM prices WHERE coin_id = ? AND currency = ? "
            "AND created_at >= ? ORDER BY created_at, id",
            (coin_id, currency, desde.isoformat(timespec="seconds")),
        ).fetchall()

    return [fila["price"] for fila in filas]


def load_state(db_path: str) -> dict[str, str]:
    """Lee por donde quedo cada cripto la ultima vez."""
    with _connect(db_path) as conn:
        filas = conn.execute("SELECT coin_id, estado FROM alert_state").fetchall()

    return {fila["coin_id"]: fila["estado"] for fila in filas}


def save_state(db_path: str, estado: dict[str, str]) -> None:
    """Guarda por donde va cada cripto, pisando lo anterior."""
    if not estado:
        return

    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    filas = [(coin_id, zona, ahora) for coin_id, zona in estado.items()]

    with _connect(db_path) as conn:
        # REPLACE actualiza si el coin_id ya existe, inserta si no.
        conn.executemany(
            "INSERT OR REPLACE INTO alert_state (coin_id, estado, updated_at) "
            "VALUES (?, ?, ?)",
            filas,
        )


def silenciar_hasta(db_path: str, cuando: datetime | None) -> None:
    """Guarda hasta cuando no se avisa. None quita el silencio."""
    with _connect(db_path) as conn:
        if cuando is None:
            conn.execute("DELETE FROM ajustes WHERE clave = ?", (SILENCIO,))
            return

        conn.execute(
            "INSERT OR REPLACE INTO ajustes (clave, valor) VALUES (?, ?)",
            (SILENCIO, cuando.isoformat(timespec="seconds")),
        )


def silenciado_hasta(db_path: str) -> datetime | None:
    """Hasta cuando estan callados los avisos, o None si no lo estan."""
    with _connect(db_path) as conn:
        fila = conn.execute(
            "SELECT valor FROM ajustes WHERE clave = ?", (SILENCIO,)
        ).fetchone()

    if not fila:
        return None

    try:
        cuando = datetime.fromisoformat(fila["valor"])
    except ValueError:
        logger.warning("El silencio guardado no se entiende: %r", fila["valor"])
        return None

    # Ya paso la hora: se acabo el silencio.
    if cuando <= datetime.now(timezone.utc):
        return None

    return cuando


def ultimo_resumen(db_path: str) -> date | None:
    """Dia en que se mando el ultimo resumen diario."""
    with _connect(db_path) as conn:
        fila = conn.execute(
            "SELECT valor FROM ajustes WHERE clave = ?", (ULTIMO_RESUMEN,)
        ).fetchone()

    if not fila:
        return None

    try:
        return date.fromisoformat(fila["valor"])
    except ValueError:
        return None


def guardar_resumen(db_path: str, dia: date) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO ajustes (clave, valor) VALUES (?, ?)",
            (ULTIMO_RESUMEN, dia.isoformat()),
        )


def ultimo_brusco(db_path: str, coin_id: str) -> datetime | None:
    """Cuando se aviso del ultimo movimiento brusco de esta cripto."""
    with _connect(db_path) as conn:
        fila = conn.execute(
            "SELECT valor FROM ajustes WHERE clave = ?", (f"brusco:{coin_id}",)
        ).fetchone()

    if not fila:
        return None

    try:
        return datetime.fromisoformat(fila["valor"])
    except ValueError:
        return None


def guardar_brusco(db_path: str, coin_id: str, cuando: datetime) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO ajustes (clave, valor) VALUES (?, ?)",
            (f"brusco:{coin_id}", cuando.isoformat(timespec="seconds")),
        )


def crear_puntual(
    db_path: str, coin_id: str, objetivo: float, sube: bool, currency: str
) -> Puntual:
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO alertas_puntuales "
            "(coin_id, objetivo, sube, currency, created_at) VALUES (?, ?, ?, ?, ?)",
            (coin_id, objetivo, int(sube), currency, ahora),
        )
    return Puntual(cursor.lastrowid, coin_id, objetivo, sube)


def get_puntuales(db_path: str, currency: str) -> list[Puntual]:
    """Las alertas pendientes. Las de otra moneda no cuentan, saltarian mal."""
    with _connect(db_path) as conn:
        filas = conn.execute(
            "SELECT id, coin_id, objetivo, sube FROM alertas_puntuales "
            "WHERE currency = ? ORDER BY id",
            (currency,),
        ).fetchall()

    return [
        Puntual(f["id"], f["coin_id"], f["objetivo"], bool(f["sube"])) for f in filas
    ]


def borrar_puntual(db_path: str, alerta_id: int) -> bool:
    """Quita una alerta. False si no existia."""
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM alertas_puntuales WHERE id = ?", (alerta_id,)
        )
        return cursor.rowcount > 0


def guardar_cambio(db_path: str, coin_id: str, regla: str | None) -> None:
    """Apunta un /vigilar o un /dejar. None es que la dejas."""
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO watchlist_cambios "
            "(coin_id, regla, de_cero, updated_at) VALUES (?, ?, 1, ?)",
            (coin_id, regla, ahora),
        )


def get_cambios(db_path: str) -> dict[str, str | None]:
    """Los cambios de Telegram, en el orden en que los hiciste."""
    with _connect(db_path) as conn:
        filas = conn.execute(
            "SELECT coin_id, regla FROM watchlist_cambios ORDER BY rowid"
        ).fetchall()

    return {f["coin_id"]: f["regla"] for f in filas}


def tomar_de_cero(db_path: str) -> set[str]:
    """Las que acaban de cambiar de regla. Las devuelve una sola vez."""
    with _connect(db_path) as conn:
        filas = conn.execute(
            "SELECT coin_id FROM watchlist_cambios WHERE de_cero = 1"
        ).fetchall()
        conn.execute("UPDATE watchlist_cambios SET de_cero = 0 WHERE de_cero = 1")

    return {f["coin_id"] for f in filas}


def get_history(db_path: str, coin_id: str, limit: int = 50) -> list[sqlite3.Row]:
    """Historico de una cripto, del mas reciente al mas antiguo."""
    with _connect(db_path) as conn:
        return conn.execute(
            "SELECT coin_id, price, currency, created_at FROM prices "
            "WHERE coin_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (coin_id, limit),
        ).fetchall()
