"""Envia mensajes por Telegram usando la API HTTP del bot."""

import html
import logging

import requests

logger = logging.getLogger(__name__)

API_URL = "https://api.telegram.org/bot{token}/sendMessage"
UPDATES_URL = "https://api.telegram.org/bot{token}/getUpdates"
COMMANDS_URL = "https://api.telegram.org/bot{token}/setMyCommands"
PHOTO_URL = "https://api.telegram.org/bot{token}/sendPhoto"

# El pie de una foto admite mucho menos que un mensaje.
MAX_CAPTION = 1024

TIMEOUT = 15

# Telegram corta los mensajes mas largos que esto.
MAX_LENGTH = 4096


class TelegramError(Exception):
    """No se pudo enviar el mensaje."""


def send_message(token: str, chat_id: str, text: str, sin_sonido: bool = False) -> bool:
    """Manda un mensaje al chat. Devuelve True si se envio.

    No lanza excepcion: un fallo de Telegram no deberia tumbar el
    programa, asi que lo registra y devuelve False.
    """
    if not text.strip():
        logger.warning("Mensaje vacio, no se envia nada")
        return False

    text = _recortar(text, MAX_LENGTH)

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        # Sin previsualizaciones de enlaces, ensucian el aviso.
        "disable_web_page_preview": True,
        # Llega igual, pero sin sonar ni vibrar.
        "disable_notification": sin_sonido,
    }

    try:
        response = requests.post(
            API_URL.format(token=token), json=payload, timeout=TIMEOUT
        )
        data = response.json()
    except requests.Timeout:
        logger.error("Telegram tardo mas de %ds en responder", TIMEOUT)
        return False
    except requests.ConnectionError:
        logger.error("Sin conexion con Telegram")
        return False
    except requests.RequestException as e:
        logger.error("Fallo el envio a Telegram: %s", e)
        return False
    except ValueError:
        logger.error("Telegram devolvio algo que no es JSON")
        return False

    # Telegram siempre contesta JSON con un campo "ok", incluso en los errores.
    if not data.get("ok"):
        logger.error(
            "Telegram rechazo el mensaje: %s", _explain(response.status_code, data)
        )
        return False

    logger.debug("Mensaje enviado al chat %s", chat_id)
    return True


def _recortar(text: str, limite: int) -> str:
    """Deja el texto por debajo del limite de Telegram sin partir etiquetas."""
    if len(text) <= limite:
        return text

    aviso = "\n[...cortado]"
    # Cortando en un salto de linea nunca queda un <b> a medias: nuestros
    # mensajes abren y cierran cada etiqueta en la misma linea.
    corte = text.rfind("\n", 0, limite - len(aviso))
    if corte <= 0:
        # Una sola linea enorme: mejor que llegue algo que un rechazo seguro.
        corte = limite - len(aviso)
    return text[:corte] + aviso


def _explain(status: int, data: dict) -> str:
    """Traduce los errores tipicos de Telegram a algo accionable."""
    descripcion = data.get("description", "sin detalle")

    if status == 401:
        return f"{descripcion}. Revisa TELEGRAM_BOT_TOKEN."
    if status == 400 and "chat not found" in descripcion.lower():
        return (
            f"{descripcion}. Revisa TELEGRAM_CHAT_ID y escribe /start "
            "a tu bot al menos una vez."
        )
    if status == 403:
        return f"{descripcion}. Has bloqueado al bot o nunca le escribiste."
    if status == 429:
        return f"{descripcion}. Demasiados mensajes seguidos."
    if status == 409:
        return f"{descripcion}. Hay otro programa leyendo los mensajes de este bot."
    return f"HTTP {status}: {descripcion}"


def send_photo(token: str, chat_id: str, png: bytes, caption: str = "") -> bool:
    """Manda una imagen con su pie. Como send_message, no lanza excepciones."""
    caption = _recortar(caption, MAX_CAPTION)

    try:
        response = requests.post(
            PHOTO_URL.format(token=token),
            data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
            files={"photo": ("grafica.png", png, "image/png")},
            timeout=TIMEOUT,
        )
        data = response.json()
    except requests.RequestException as e:
        logger.error("Fallo el envio de la imagen a Telegram: %s", e)
        return False
    except ValueError:
        logger.error("Telegram devolvio algo que no es JSON")
        return False

    if not data.get("ok"):
        logger.error(
            "Telegram rechazo la imagen: %s", _explain(response.status_code, data)
        )
        return False
    return True


def get_updates(token: str, offset: int | None, espera: int) -> list[dict]:
    """Recoge los mensajes nuevos. Si no hay, espera hasta `espera` segundos.

    Pedir con offset le dice a Telegram que los anteriores ya los tenemos.
    """
    params = {"timeout": espera, "allowed_updates": '["message"]'}
    if offset is not None:
        params["offset"] = offset

    try:
        response = requests.get(
            UPDATES_URL.format(token=token), params=params, timeout=TIMEOUT + espera
        )
        data = response.json()
    except requests.RequestException as e:
        raise TelegramError(f"No se pudieron leer los mensajes: {e}") from e
    except ValueError as e:
        raise TelegramError("Telegram devolvio algo que no es JSON") from e

    if not data.get("ok"):
        raise TelegramError(_explain(response.status_code, data))

    return data.get("result", [])


def set_commands(token: str, comandos: dict[str, str]) -> bool:
    """Rellena el menu que sale al escribir "/" en el chat."""
    payload = {
        "commands": [
            {"command": nombre, "description": texto}
            for nombre, texto in comandos.items()
        ]
    }
    try:
        response = requests.post(
            COMMANDS_URL.format(token=token), json=payload, timeout=TIMEOUT
        )
        return bool(response.json().get("ok"))
    except (requests.RequestException, ValueError):
        return False


def escape(text: str) -> str:
    """Escapa el texto para que Telegram no lo confunda con etiquetas HTML."""
    return html.escape(str(text), quote=False)
