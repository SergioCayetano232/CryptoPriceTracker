"""Lo que el bot te vuelve a preguntar más tarde: /recordar, /pienso y /prediccion."""

import logging
import math
from dataclasses import replace
from datetime import datetime, timezone

from .. import (
    alerts,
    botones,
    coingecko,
    database,
    miedo,
    pienso,
    prediccion,
    recordar,
    telegram,
)
from ..config import Config
from .base import _con_cambios, _indicador, _silenciado

logger = logging.getLogger("crypto_tracker")


def _recordar(config: Config, argumento: str) -> str:
    hora = _con_cambios(config).resumen_diario or recordar.HORA
    if not argumento:
        lista = database.get_recordatorios(config.database_path)
        return alerts.formatear_recordatorios(lista, config.vs_currency, hora)

    quitar = recordar.para_quitar(argumento)
    if quitar:
        if database.quitar_recordatorio(config.database_path, quitar):
            return f"Hecho, ya no te recuerdo la compra de {telegram.escape(quitar)}."
        return "No tenías ningún recordatorio de esa. Mira /recordar"

    try:
        r = recordar.interpretar(argumento)
    except recordar.RecordarError as e:
        return telegram.escape(str(e))

    # El precio, para decirte cuánto sale, y de paso ver que la cripto existe.
    try:
        precio = coingecko.get_prices([r.coin_id], config.vs_currency).get(r.coin_id)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirar el precio ahora mismo: {telegram.escape(str(e))}"
    if precio is None:
        return (
            f"No encuentro <b>{telegram.escape(r.coin_id)}</b> en CoinGecko. "
            f"Prueba con /buscar {telegram.escape(r.coin_id)}"
        )

    database.guardar_recordatorio(config.database_path, r)
    logger.info("Recordatorio: %s cada %s de %s", r.importe, r.nombre_dia, r.coin_id)
    return alerts.con_fuente(
        alerts.formatear_recordatorio(r, precio, config.vs_currency, hora)
    )


def _pienso(config: Config, argumento: str) -> str:
    if not argumento:
        return alerts.formatear_piensos(
            database.get_piensos(config.database_path), config.vs_currency
        )
    try:
        coin_id, importe = pienso.interpretar(argumento)
    except pienso.PiensoError as e:
        return telegram.escape(str(e))

    if importe is None:
        # Lo mismo si lo quitas tú que si le das al botón cuando ya pregunté.
        database.quitar_pienso(config.database_path, coin_id)
        return (
            "👍 Vale, no apunto nada. Mejor una compra que no haces que una que "
            "lamentas"
        )

    try:
        precio = coingecko.get_prices([coin_id], config.vs_currency).get(coin_id)
    except coingecko.CoinGeckoError as e:
        return f"No he podido consultar el precio: {telegram.escape(str(e))}"
    if precio is None:
        return (
            f"No encuentro <b>{telegram.escape(coin_id)}</b> en CoinGecko. "
            f"Prueba con /buscar {telegram.escape(coin_id)}"
        )

    p = pienso.Pienso(coin_id, importe, precio, datetime.now(timezone.utc))
    database.guardar_pienso(config.database_path, p)

    # Lo de alrededor es un extra: si algo falla, se contesta sin esa línea.
    try:
        hoy = miedo.pedir()
    except miedo.MiedoError as e:
        logger.warning("/pienso sin el índice de miedo: %s", e)
        hoy = []
    return alerts.con_fuente(
        alerts.formatear_pienso(
            p,
            config.vs_currency,
            coingecko.cambio_24h(coin_id),
            hoy[0] if hoy else None,
            _indicador(config, "rsi", coin_id),
        )
    )


def _prediccion(config: Config, argumento: str) -> str:
    todas = database.get_predicciones(config.database_path, config.vs_currency)
    if not argumento:
        pendientes = [p for p in todas if p.real is None]
        return alerts.formatear_predicciones(
            pendientes, prediccion.marcador(todas), config.vs_currency
        )
    try:
        coin_id, valor = prediccion.interpretar(argumento)
    except prediccion.PrediccionError as e:
        return telegram.escape(str(e))

    if valor is None:
        if database.quitar_prediccion(
            config.database_path, coin_id, config.vs_currency
        ):
            return f"Hecho, quitada la de <b>{telegram.escape(coin_id)}</b>."
        return "No tenías ninguna en juego de esa. Mira /prediccion"

    ahora = datetime.now(timezone.utc)
    cierre = prediccion.cierre(ahora)
    # Cambiarla a última hora la mandaría al domingo siguiente y borraría esta.
    antes = next((p for p in todas if p.coin_id == coin_id and p.real is None), None)
    if antes and antes.cierre != cierre:
        return (
            f"La de <b>{telegram.escape(coin_id)}</b> se cierra el "
            f"{antes.cierre.astimezone():%d/%m a las %H:%M} y ya no se puede "
            "cambiar. Después pones la de la semana que viene"
        )

    try:
        precio = coingecko.get_prices([coin_id], config.vs_currency).get(coin_id)
    except coingecko.CoinGeckoError as e:
        return f"No he podido consultar el precio: {telegram.escape(str(e))}"
    if precio is None:
        return (
            f"No encuentro <b>{telegram.escape(coin_id)}</b> en CoinGecko. "
            f"Prueba con /buscar {telegram.escape(coin_id)}"
        )
    if valor == precio:
        return "Eso es justo lo que vale ahora. Moja un poco: ¿sube o baja?"

    p = database.guardar_prediccion(
        config.database_path,
        prediccion.Prediccion(None, coin_id, ahora, cierre, precio, valor),
        config.vs_currency,
    )
    return alerts.con_fuente(alerts.formatear_prediccion(p, config.vs_currency))


def cerrar_predicciones(config: Config, ahora: datetime | None = None) -> None:
    """El domingo a las 20:00, cómo han quedado y el marcador."""
    ahora = ahora or datetime.now(timezone.utc)
    try:
        todas = database.get_predicciones(config.database_path, config.vs_currency)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer las predicciones: %s", e)
        return
    tocan = prediccion.tocan(todas, ahora)
    if not tocan or _silenciado(config):
        return

    hechas = []
    for p in tocan:
        real = _precio_del_cierre(config, p, ahora)
        if real is None:
            continue  # lo intento en el ciclo siguiente
        database.cerrar_prediccion(config.database_path, p.id, real)
        hechas.append(replace(p, real=real))
    if not hechas:
        return

    cerradas = {p.id: p for p in hechas}
    todas = [cerradas.get(p.id, p) for p in todas]
    telegram.send_message(
        config.telegram_token,
        config.telegram_chat_id,
        alerts.con_fuente(
            alerts.formatear_resultado(
                hechas, prediccion.marcador(todas), config.vs_currency
            )
        ),
    )
    logger.info("Predicciones cerradas: %s", ", ".join(p.coin_id for p in hechas))


def _precio_del_cierre(
    config: Config, p: prediccion.Prediccion, ahora: datetime
) -> float | None:
    """El de las 20:00 del domingo, aunque el bot estuviera apagado entonces."""
    horas = (ahora - p.cierre).total_seconds() / 3600 + 3
    serie = database.get_serie(
        config.database_path, p.coin_id, horas, config.vs_currency
    )
    real = prediccion.precio_del_cierre(serie, p.cierre)
    if real is not None:
        return real
    try:
        dias = max(1, math.ceil(horas / 24))
        bajados = coingecko.historico(p.coin_id, dias, config.vs_currency)
    except coingecko.CoinGeckoError as e:
        logger.warning("Sin precio del domingo de %s: %s", p.coin_id, e)
        return None
    return prediccion.precio_del_cierre(bajados, p.cierre)


def pensados(config: Config, ahora: datetime | None = None) -> None:
    """A las 24 h de cada /pienso, la pregunta con el precio de entonces."""
    ahora = ahora or datetime.now(timezone.utc)
    try:
        tocan = pienso.tocan(database.get_piensos(config.database_path), ahora)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer los /pienso: %s", e)
        return
    # Callado, se queda esperando y pregunta al volver.
    if not tocan or _silenciado(config):
        return

    try:
        precios = coingecko.get_prices([p.coin_id for p in tocan], config.vs_currency)
    except coingecko.CoinGeckoError as e:
        logger.warning("Sin precio para los /pienso: %s", e)
        return

    for p in tocan:
        precio = precios.get(p.coin_id)
        if precio is None:
            continue
        if not telegram.send_message(
            config.telegram_token,
            config.telegram_chat_id,
            alerts.con_fuente(alerts.formatear_pensado(p, precio, config.vs_currency)),
            botones=botones.para_pienso(pienso.comando_compra(p, precio), p.coin_id),
        ):
            logger.error("No se pudo preguntar por el /pienso de %s", p.coin_id)
            continue
        # Ya está preguntado: lo que diga el botón es lo que vale.
        database.quitar_pienso(config.database_path, p.coin_id)
        logger.info("/pienso de %s preguntado", p.coin_id)


def recordatorios(config: Config, ahora: datetime | None = None) -> None:
    """El día de cada /recordar, a la hora del resumen, el aviso con su botón."""
    ahora = ahora or datetime.now().astimezone()
    hora = _con_cambios(config).resumen_diario
    try:
        lista = database.get_recordatorios(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer los recordatorios: %s", e)
        return
    tocan = [r for r in lista if recordar.toca(r, ahora, hora)]
    if not tocan or _silenciado(config):
        return

    try:
        precios = coingecko.get_prices([r.coin_id for r in tocan], config.vs_currency)
    except coingecko.CoinGeckoError as e:
        # Sin precio no hay cantidad que apuntar: se reintenta el ciclo siguiente.
        logger.warning("Sin precio para los recordatorios: %s", e)
        return

    for r in tocan:
        precio = precios.get(r.coin_id)
        if precio is None:
            logger.warning("Sin precio de %s para su recordatorio", r.coin_id)
            continue
        if not telegram.send_message(
            config.telegram_token,
            config.telegram_chat_id,
            alerts.con_fuente(
                alerts.formatear_toca_comprar(r, precio, config.vs_currency)
            ),
            botones=botones.para_recordatorio(
                recordar.comando_compra(r, precio), r.coin_id
            ),
        ):
            logger.error("No se pudo mandar el recordatorio de %s", r.coin_id)
            continue
        database.guardar_recordatorio(
            config.database_path, replace(r, ultimo=ahora.date())
        )
        logger.info("Recordatorio de %s enviado", r.coin_id)
