"""Envia mensajes por Telegram usando la API HTTP del bot."""

import html
import logging

import requests

logger = logging.getLogger(__name__)

API_URL = "https://api.telegram.org/bot{token}/sendMessage"

TIMEOUT = 15

# Telegram corta los mensajes mas largos que esto.
MAX_LENGTH = 4096


class TelegramError(Exception):
    """No se pudo enviar el mensaje."""


def send_message(token: str, chat_id: str, text: str) -> bool:
    """Manda un mensaje al chat. Devuelve True si se envio.

    No lanza excepcion: un fallo de Telegram no deberia tumbar el
    programa, asi que lo registra y devuelve False.
    """
    if not text.strip():
        logger.warning("Mensaje vacio, no se envia nada")
        return False

    if len(text) > MAX_LENGTH:
        # Cortamos dejando sitio para el aviso, mejor eso que un 400.
        text = text[: MAX_LENGTH - 20] + "\n[...cortado]"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        # Sin previsualizaciones de enlaces, ensucian el aviso.
        "disable_web_page_preview": True,
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
    return f"HTTP {status}: {descripcion}"


def escape(text: str) -> str:
    """Escapa el texto para que Telegram no lo confunda con etiquetas HTML."""
    return html.escape(str(text), quote=False)
