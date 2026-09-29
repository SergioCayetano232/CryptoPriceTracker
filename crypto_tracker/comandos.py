"""Entiende los comandos que le escribes al bot por Telegram."""

from dataclasses import dataclass

# Lo que sale en el menu de Telegram al escribir "/".
COMANDOS = {
    "status": "Cómo van tus criptos ahora",
    "historico": "Cómo ha ido una cripto en 24 h (ej: /historico bitcoin)",
    "buscar": "Encuentra el id de una cripto (ej: /buscar btc)",
    "mute": "Callar los avisos un rato (ej: /mute 2h)",
    "unmute": "Volver a avisar",
    "ayuda": "Lo que sé hacer",
}

# /start lo manda Telegram solo la primera vez que abres el chat.
ALIAS = {
    "start": "ayuda",
    "help": "ayuda",
    "history": "historico",
    "search": "buscar",
}

AYUDA = "🤖 <b>Esto es lo que sé hacer</b>\n\n" + "\n".join(
    f"/{nombre} — {texto}" for nombre, texto in COMANDOS.items()
)

NO_ENTIENDO = "No te entiendo. Escribe /ayuda para ver lo que sé hacer."


@dataclass(frozen=True)
class Foto:
    """Una respuesta con imagen. texto es lo que se manda si la imagen no pasa."""

    png: bytes
    pie: str
    texto: str


def interpretar(texto: str) -> tuple[str, str] | None:
    """'/mute@MiBot 2h' -> ('mute', '2h'). None si no es un comando."""
    partes = texto.strip().split(maxsplit=1)
    if not partes or not partes[0].startswith("/"):
        return None

    # En los grupos Telegram le pega el nombre del bot: /status@MiBot
    nombre = partes[0][1:].split("@")[0].lower()
    argumento = partes[1].strip() if len(partes) > 1 else ""
    return ALIAS.get(nombre, nombre), argumento
