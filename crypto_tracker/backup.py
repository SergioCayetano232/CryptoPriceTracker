"""/backup: la base de datos en un zip, por si se muere el servidor."""

import io
import tempfile
import zipfile
from datetime import date
from pathlib import Path

from . import database

DIAS = 7

# Lo máximo que Telegram deja subir a un bot.
MAX_BYTES = 50 * 1024 * 1024

GRANDE = (
    "📦 La copia pasa de 50 MB y Telegram no me deja mandarla. "
    "Baja HISTORY_DAYS o cópiala a mano del servidor."
)
FALLO = "No he podido mandarte la copia. Prueba en un rato."


def toca(ultima: date | None, hoy: date) -> bool:
    return ultima is None or (hoy - ultima).days >= DIAS


def nombre(hoy: date) -> str:
    return f"copia-cryptotracker-{hoy:%Y-%m-%d}.zip"


def pie(hoy: date) -> str:
    return (
        f"📦 <b>Copia de seguridad del {hoy:%d/%m/%Y}</b>\n"
        "Precios, compras, ventas y alertas. Lo del .env no va aquí: eso, con /copia."
    )


def crear(db_path: str) -> bytes:
    """El zip con la base de datos. Zip y no gz porque Windows lo abre solo."""
    with tempfile.TemporaryDirectory() as carpeta:
        copia = Path(carpeta) / Path(db_path).name
        database.volcar(db_path, str(copia))
        salida = io.BytesIO()
        with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as archivo:
            archivo.write(copia, copia.name)
    return salida.getvalue()
