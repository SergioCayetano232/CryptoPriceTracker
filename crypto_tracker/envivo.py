"""El mensaje fijado de /envivo, que el bot va editando en vez de mandar otro."""

from datetime import datetime

TITULO = "📌 <b>En vivo</b>"

_QUITAR = frozenset({"no", "off", "quitar", "quita", "parar", "para", "fuera"})

# Lo que contesta Telegram cuando el mensaje ya no está o no nos deja tocarlo.
# Con esto no tiene sentido insistir cada ciclo.
_PERDIDO = (
    "message to edit not found",
    "message can't be edited",
    "message_id_invalid",
    "chat not found",
    "bot was blocked",
)


class EnvivoError(Exception):
    """No se entiende lo que le pides a /envivo."""


def interpretar(argumento: str) -> bool:
    """True es ponerlo (o bajarlo al final del chat); False, quitarlo."""
    palabra = argumento.strip().lower()
    if not palabra:
        return True
    if palabra in _QUITAR:
        return False
    raise EnvivoError("No te entiendo. /envivo lo pone y /envivo no lo quita.")


def se_perdio(error: str) -> bool:
    """Si con ese error de Telegram hay que dejar de editarlo."""
    error = error.lower()
    return any(frase in error for frase in _PERDIDO)


def pie(ahora: datetime) -> str:
    return f"<i>Actualizado a las {ahora:%H:%M} · /envivo no lo quita</i>"
