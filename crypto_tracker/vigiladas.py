"""Lo que vigilas: el .env de base y, encima, lo que cambies por Telegram."""

import logging

from .config import ConfigError, Watch, parse_entrada
from .puntuales import numero

logger = logging.getLogger(__name__)

EJEMPLOS = "/vigilar solana %5, /vigilar solana 10 o /vigilar bitcoin 55000 75000"


class VigilarError(Exception):
    """Lo que escribiste en /vigilar no se entiende."""


def interpretar(argumento: str) -> tuple[Watch, str]:
    """'solana %5' -> el Watch y la regla tal cual va en el .env ('solana:%5')."""
    partes = argumento.split()
    if len(partes) not in (2, 3):
        raise VigilarError(f"Escríbelo así: {EJEMPLOS}")

    coin_id = partes[0].lower()
    if len(partes) == 2:
        valor = partes[1]
        # 5% y %5, que lo natural es ponerlo detras
        es_pct = valor.startswith("%") or valor.endswith("%")
        regla = f"{coin_id}:{'%' if es_pct else ''}{_numero(valor.strip('%'))}"
    else:
        # Un guion deja ese lado sin vigilar, como el hueco en ethereum::4000
        minimo, maximo = ("" if x == "-" else str(_numero(x)) for x in partes[1:])
        regla = f"{coin_id}:{minimo}:{maximo}"

    try:
        return parse_entrada(regla), regla
    except ConfigError as e:
        raise VigilarError(str(e)) from None


def _numero(texto: str) -> float:
    valor = numero(texto)
    if valor is None:
        raise VigilarError(f"'{texto}' no es un número. Ejemplos: {EJEMPLOS}")
    return valor


def combinar(base: list[Watch], cambios: dict[str, str | None]) -> list[Watch]:
    """Aplica los cambios de Telegram. None en un cambio es que la dejaste."""
    resultado = []
    for watch in base:
        if watch.coin_id in cambios:
            watch = _leer(cambios[watch.coin_id], watch)
        if watch is not None:
            resultado.append(watch)

    del_env = {w.coin_id for w in base}
    for coin_id, regla in cambios.items():
        if coin_id not in del_env:
            nueva = _leer(regla, None)
            if nueva is not None:
                resultado.append(nueva)

    return resultado


def _leer(regla: str | None, si_falla: Watch | None) -> Watch | None:
    if regla is None:
        return None
    try:
        return parse_entrada(regla)
    except ConfigError as e:
        # No deberia pasar, se valida al guardarla. Pero si pasa, que no tumbe el bot.
        logger.error("Regla guardada que no se entiende (%s): %s", regla, e)
        return si_falla
