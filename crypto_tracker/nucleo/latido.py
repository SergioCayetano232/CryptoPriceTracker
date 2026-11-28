"""Un toque a una URL de fuera cada vez que un ciclo sale bien.

Si se cae el servidor entero, el bot no puede avisarte de que está muerto. Un
servicio como healthchecks.io sí: deja de recibir el toque y te escribe él.
"""

import logging
from urllib.parse import urlsplit

import requests

logger = logging.getLogger("crypto_tracker")

# Corto a propósito: va dentro del ciclo y no puede retrasar los avisos.
TIMEOUT = 10


def servicio(url: str) -> str:
    """Solo el dominio. El resto de la URL es la clave y no se enseña."""
    return urlsplit(url).hostname or "?"


def mandar(url: str) -> bool:
    """Da el toque. Si falla no pasa nada: el siguiente ciclo da otro."""
    try:
        respuesta = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as e:
        # Sin la URL en el log, que lleva la clave.
        logger.warning("No se pudo dar el latido: %s", type(e).__name__)
        return False
    if respuesta.status_code >= 400:
        logger.warning("El latido devolvio un %d", respuesta.status_code)
        return False
    return True
