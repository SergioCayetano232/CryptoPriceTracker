"""Lo que comparten las respuestas a los comandos y el bucle."""

import logging
from dataclasses import replace
from datetime import datetime

from .. import (
    alertaratio,
    alerts,
    cartera,
    coingecko,
    comandos,
    database,
    diario,
    direccion,
    movimientos,
    telegram,
    vigiladas,
)
from ..config import Config, Posicion

logger = logging.getLogger("crypto_tracker")


# Con cuanto tiempo atras se compara el precio en el resumen.
HORAS_RESUMEN = 24


def _con_cambios(config: Config) -> Config:
    """La config de verdad: el .env mas lo que cambias por Telegram."""
    try:
        cambios = database.get_cambios(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer los cambios de /vigilar: %s", e)
        cambios = {}
    if cambios:
        config = replace(
            config, watchlist=vigiladas.combinar(config.watchlist, cambios)
        )

    try:
        de_cartera = database.get_cambios_cartera(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer las compras y ventas: %s", e)
        de_cartera = {}
    if de_cartera:
        config = replace(
            config, cartera=movimientos.combinar(config.cartera, de_cartera)
        )

    try:
        cambiada, hora = database.hora_resumen(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudo leer la hora del resumen: %s", e)
        cambiada = False
    if cambiada:
        config = replace(config, resumen_diario=hora)
    return config


Respuesta = str | comandos.Foto | comandos.Archivo | comandos.ConBotones


SIN_CARTERA = (
    "No tienes cartera puesta. Apunta lo que tienes con "
    "/compra bitcoin 0.016 1000, o añade al .env algo como:\n"
    "<code>PORTFOLIO=bitcoin:0.016:1000</code>"
)


def _precio_o_pedirlo(config: Config, coin_id: str) -> float | str:
    """El último guardado y, si no hay, una consulta. Un str es el error."""
    precio = database.get_last_price(config.database_path, coin_id)
    if precio:
        return precio
    # Si no la vigilas no la tengo guardada: una consulta y listo.
    try:
        precio = coingecko.get_prices([coin_id], config.vs_currency).get(coin_id)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirar el precio ahora mismo: {telegram.escape(str(e))}"
    if not precio:
        return alerts.formatear_no_encuentro([coin_id])
    return precio


def _valor_guardado(config: Config) -> float | str:
    """Lo que vale la cartera, con lo guardado si lo hay. Si no se puede, el porqué."""
    posiciones = list(_con_cambios(config).cartera)
    if not posiciones:
        return SIN_CARTERA
    precios = _precios_guardados(config, posiciones)
    valor = cartera.valor_total(posiciones, precios)
    if valor is None:
        return "No he podido consultar los precios. Prueba en un rato."
    return valor


def _precios_guardados(config: Config, posiciones: list[Posicion]) -> dict[str, float]:
    """Los últimos guardados y, de lo que falte, una consulta."""
    precios = {}
    for p in posiciones:
        precio = database.get_last_price(config.database_path, p.coin_id)
        if precio:
            precios[p.coin_id] = precio
    faltan = [p.coin_id for p in posiciones if p.coin_id not in precios]
    if faltan:
        precios.update(_consultar(config, faltan) or {})
    return precios


def _consultar(config: Config, coin_ids: list[str]) -> dict[str, float] | None:
    """Pide los precios y los guarda. None si no hay ninguno."""
    try:
        precios = coingecko.get_prices(coin_ids, config.vs_currency)
    except coingecko.CoinGeckoError as e:
        logger.error("No se pudieron consultar los precios: %s", e)
        return None

    if not precios:
        logger.error("La consulta no devolvio ningun precio")
        return None

    # Aprovechamos la consulta para guardarla, asi el resumen tambien
    # alimenta el historico con el que se compara la proxima vez.
    try:
        database.save_prices(config.database_path, precios, config.vs_currency)
    except database.DatabaseError as e:
        logger.error("No se pudo guardar en la base de datos: %s", e)

    return precios


def _variacion(config: Config, coin_id: str, precio: float) -> float | None:
    """Cuanto ha variado en porcentaje desde hace HORAS_RESUMEN horas."""
    # La de CoinGecko vale aunque el bot lleve poco funcionando o haya estado
    # apagado. El historico propio queda de reserva.
    cambio = coingecko.cambio_24h(coin_id)
    if cambio is not None:
        return cambio

    try:
        antes = database.get_price_at(config.database_path, coin_id, HORAS_RESUMEN)
    except database.DatabaseError as e:
        logger.warning("No se pudo leer el historico de %s: %s", coin_id, e)
        return None

    if not antes:
        return None

    return (precio - antes) / antes * 100


def _silenciado(config: Config) -> datetime | None:
    """Hasta cuando estan callados los avisos, si es que lo estan."""
    try:
        return database.silenciado_hasta(config.database_path)
    except database.DatabaseError as e:
        # Si no podemos leerlo, mejor avisar de mas que quedarnos mudos.
        logger.warning("No se pudo leer el silencio: %s", e)
        return None


def _sin_sonido(config: Config, ahora: datetime | None = None) -> bool:
    """True si estamos en HORAS_TRANQUILAS: los avisos llegan, pero sin sonar."""
    if config.horas_tranquilas is None:
        return False

    ahora = ahora or datetime.now().astimezone()
    return diario.es_hora_tranquila(ahora.time(), *config.horas_tranquilas)


def _alertas_ratio(config: Config) -> list[alertaratio.AlertaRatio]:
    try:
        return database.get_alertas_ratio(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer las alertas de ratio: %s", e)
        return []


def _direcciones_guardadas(config: Config) -> list[direccion.Vigilada]:
    guardadas = database.direcciones(config.database_path)
    lista = [direccion.cargar(d, v) for d, v in guardadas.items()]
    return [v for v in lista if v is not None]
