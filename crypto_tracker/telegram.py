"""Envia mensajes por Telegram usando la API HTTP del bot."""

import html
import json
import logging
import time

import requests

logger = logging.getLogger(__name__)

API_URL = "https://api.telegram.org/bot{token}/sendMessage"
UPDATES_URL = "https://api.telegram.org/bot{token}/getUpdates"
COMMANDS_URL = "https://api.telegram.org/bot{token}/setMyCommands"
PHOTO_URL = "https://api.telegram.org/bot{token}/sendPhoto"
DOCUMENT_URL = "https://api.telegram.org/bot{token}/sendDocument"
ANSWER_URL = "https://api.telegram.org/bot{token}/answerCallbackQuery"

# El pie de una foto admite mucho menos que un mensaje.
MAX_CAPTION = 1024

TIMEOUT = 15
# Subir una copia de varios MB con una conexión normalita tarda más que un texto.
TIMEOUT_ARCHIVO = 120

# Telegram corta los mensajes mas largos que esto.
MAX_LENGTH = 4096

# Como en CoinGecko: tres intentos esperando 2s y luego 4s. Un corte corto de
# red ya no nos hace perder el aviso.
INTENTOS = 3
ESPERA_INICIAL = 2
# Si con un 429 nos piden esperar más que esto, lo dejo: el bucle no puede
# quedarse parado minutos por un mensaje.
ESPERA_MAXIMA = 30


class TelegramError(Exception):
    """No se pudo enviar el mensaje."""


def send_message(
    token: str,
    chat_id: str,
    text: str,
    sin_sonido: bool = False,
    botones: list[list[tuple[str, str]]] | None = None,
) -> bool:
    """Manda un mensaje al chat. Devuelve True si se envio.

    botones son filas de (texto, datos); los datos vuelven al pulsarlo.

    No lanza excepcion: un fallo de Telegram no deberia tumbar el
    programa, asi que reintenta los pasajeros y si no, devuelve False.
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
    if botones:
        payload["reply_markup"] = _teclado(botones)

    espera = ESPERA_INICIAL
    for intento in range(1, INTENTOS + 1):
        ok, reintentar, pide = _enviar(token, payload)
        if ok:
            logger.debug("Mensaje enviado al chat %s", chat_id)
            return True
        # Lo que pida Telegram con un 429 manda sobre nuestra espera.
        espera = max(espera, pide)
        if not reintentar or intento == INTENTOS or espera > ESPERA_MAXIMA:
            return False
        logger.warning("Reintento %d de %d en %ds", intento, INTENTOS - 1, espera)
        time.sleep(espera)
        espera *= 2

    return False


def _enviar(token: str, payload: dict) -> tuple[bool, bool, int]:
    """Un intento suelto: (enviado, merece reintentar, segundos que pide esperar)."""
    try:
        response = requests.post(
            API_URL.format(token=token), json=payload, timeout=TIMEOUT
        )
        data = response.json()
    except requests.Timeout:
        # Puede que sí llegara y salga repetido, pero mejor dos que ninguno.
        logger.error("Telegram tardo mas de %ds en responder", TIMEOUT)
        return False, True, 0
    except requests.ConnectionError:
        logger.error("Sin conexion con Telegram")
        return False, True, 0
    except requests.RequestException as e:
        logger.error("Fallo el envio a Telegram: %s", e)
        return False, True, 0
    except ValueError:
        # Suele ser una página de error de un proxy o de Telegram caído.
        logger.error("Telegram devolvio algo que no es JSON")
        return False, True, 0

    # Telegram siempre contesta JSON con un campo "ok", incluso en los errores.
    if data.get("ok"):
        return True, False, 0

    status = response.status_code
    logger.error("Telegram rechazo el mensaje: %s", _explain(status, data))
    if status == 429:
        parametros = data.get("parameters")
        pide = parametros.get("retry_after", 0) if isinstance(parametros, dict) else 0
        return False, True, pide if isinstance(pide, int) else 0
    # Un token o chat mal puesto no se arregla insistiendo; un 5xx a veces sí.
    return False, status >= 500, 0


def _teclado(botones: list[list[tuple[str, str]]]) -> dict:
    return {
        "inline_keyboard": [
            [{"text": texto, "callback_data": datos} for texto, datos in fila]
            for fila in botones
        ]
    }


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


def send_photo(
    token: str,
    chat_id: str,
    png: bytes,
    caption: str = "",
    sin_sonido: bool = False,
    botones: list[list[tuple[str, str]]] | None = None,
) -> bool:
    """Manda una imagen con su pie. Como send_message, no lanza excepciones."""
    return _mandar_archivo(
        PHOTO_URL.format(token=token),
        chat_id,
        {"photo": ("grafica.png", png, "image/png")},
        caption,
        sin_sonido,
        "la imagen",
        botones,
    )


def send_document(
    token: str,
    chat_id: str,
    contenido: bytes,
    nombre: str,
    caption: str = "",
    sin_sonido: bool = False,
) -> bool:
    """Manda un archivo adjunto, como el CSV de /exportar o la copia de /backup."""
    tipo = "application/zip" if nombre.endswith(".zip") else "text/csv"
    return _mandar_archivo(
        DOCUMENT_URL.format(token=token),
        chat_id,
        {"document": (nombre, contenido, tipo)},
        caption,
        sin_sonido,
        "el archivo",
        timeout=TIMEOUT_ARCHIVO,
    )


def _mandar_archivo(
    url: str,
    chat_id: str,
    files: dict,
    caption: str,
    sin_sonido: bool,
    que: str,
    botones: list[list[tuple[str, str]]] | None = None,
    timeout: int = TIMEOUT,
) -> bool:
    caption = _recortar(caption, MAX_CAPTION)
    datos = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
    if sin_sonido:
        datos["disable_notification"] = "true"
    if botones:
        # Con archivo va como formulario, y ahi el teclado tiene que ir en texto.
        datos["reply_markup"] = json.dumps(_teclado(botones))

    try:
        response = requests.post(url, data=datos, files=files, timeout=timeout)
        data = response.json()
    except requests.RequestException as e:
        logger.error("Fallo el envio de %s a Telegram: %s", que, e)
        return False
    except ValueError:
        logger.error("Telegram devolvio algo que no es JSON")
        return False

    if not data.get("ok"):
        logger.error(
            "Telegram rechazo %s: %s", que, _explain(response.status_code, data)
        )
        return False
    return True


def get_updates(token: str, offset: int | None, espera: int) -> list[dict]:
    """Recoge los mensajes nuevos. Si no hay, espera hasta `espera` segundos.

    Pedir con offset le dice a Telegram que los anteriores ya los tenemos.
    """
    params = {
        "timeout": espera,
        "allowed_updates": '["message", "callback_query"]',
    }
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


def answer_callback(token: str, callback_id: str) -> bool:
    """Le dice a Telegram que el boton ya se atendio, si no se queda cargando."""
    try:
        response = requests.post(
            ANSWER_URL.format(token=token),
            json={"callback_query_id": callback_id},
            timeout=TIMEOUT,
        )
        return bool(response.json().get("ok"))
    except (requests.RequestException, ValueError):
        return False


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
