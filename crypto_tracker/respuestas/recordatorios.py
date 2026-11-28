"""Lo que el bot te vuelve a preguntar más tarde: /recordar, /pienso, /tesis..."""

import logging
import math
from dataclasses import replace
from datetime import datetime, timezone

from .. import encuesta, liga, prediccion
from ..avisos import alerts, recordar
from ..indicadores import miedo
from ..inversion import pienso, tesis
from ..nucleo import botones, coingecko, database, telegram, usuarios
from ..nucleo.config import Config
from .base import (
    _con_cambios,
    _indicador,
    _precio_o_pedirlo,
    _silenciado,
    _sin_sonido,
)

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


def _mandar_encuesta(config: Config, ahora: datetime) -> encuesta.Encuesta | str:
    """Manda la de esta semana y la guarda. Si no puede, el porqué."""
    vigiladas = _con_cambios(config).watchlist
    if not vigiladas:
        return "No vigilas ninguna cripto. Empieza con /vigilar bitcoin %5"
    coin_id = vigiladas[0].coin_id
    # Lo último guardado: para preguntar no hace falta gastar una consulta.
    precio = database.get_last_price(config.database_path, coin_id)
    if not precio:
        return "Todavía no tengo precios guardados. Prueba en unos minutos."

    nueva = encuesta.Encuesta("", coin_id, precio, prediccion.cierre(ahora))
    hasta = encuesta.se_cierra(nueva.cierre)
    # Telegram no admite un cierre ya pasado ni a más de un mes.
    if not encuesta.MINIMO_TELEGRAM < hasta - ahora < encuesta.MAXIMO_TELEGRAM:
        return "Ahora mismo no puedo abrirla. Prueba en un rato."
    poll_id = telegram.enviar_encuesta(
        config.telegram_token,
        config.telegram_chat_id,
        alerts.pregunta_encuesta(nueva, config.vs_currency),
        alerts.opciones_encuesta(nueva, config.vs_currency),
        int(hasta.timestamp()),
        sin_sonido=_sin_sonido(config),
    )
    if poll_id is None:
        return "No he podido mandarte la encuesta. Prueba en un rato."
    nueva = replace(nueva, poll_id=poll_id)
    database.guardar_encuesta(config.database_path, encuesta.a_texto(nueva))
    return nueva


def _encuesta(config: Config, argumento: str) -> str:
    try:
        poner = encuesta.interpretar(argumento)
    except encuesta.EncuestaError as e:
        return str(e)
    puesta = database.encuesta(config.database_path) is not None
    if not poner:
        if not puesta:
            return "No la tenías puesta. Para ponerla: /encuesta"
        database.guardar_encuesta(config.database_path, None)
        return "Hecho, ya no te mando la encuesta de cada semana."
    if puesta:
        return (
            "Ya la tienes puesta: cada lunes te llega la de esa semana. "
            "Para quitarla: /encuesta no"
        )
    resultado = _mandar_encuesta(config, datetime.now(timezone.utc))
    if isinstance(resultado, str):
        return resultado
    return alerts.formatear_encuesta_puesta(resultado)


def encuesta_semanal(config: Config, ahora: datetime | None = None) -> None:
    """Los lunes manda la encuesta de la semana a quien tenga /encuesta puesto."""
    ahora = ahora or datetime.now(timezone.utc)
    try:
        ultima = encuesta.de_texto(database.encuesta(config.database_path))
        if ultima is None or not encuesta.toca(ahora, ultima):
            return
        if _silenciado(config):
            return
        resultado = _mandar_encuesta(config, ahora)
    except database.DatabaseError as e:
        logger.error("No se pudo mandar la encuesta de la semana: %s", e)
        return
    if isinstance(resultado, str):
        # Lo reintenta el siguiente ciclo, mientras siga siendo de lunes a miércoles.
        logger.warning("La encuesta de la semana no ha salido: %s", resultado)
    else:
        logger.info("Encuesta de la semana enviada: %s", resultado.coin_id)


def voto_encuesta(
    config: Config, poll_id: str, opciones: list[int], ahora: datetime | None = None
) -> None:
    """Un voto en la encuesta: se apunta como la /prediccion de esa semana."""
    ahora = ahora or datetime.now(timezone.utc)
    e = encuesta.de_texto(database.encuesta(config.database_path))
    # Una encuesta vieja, o de cuando la tenías puesta: ya no cuenta.
    if e is None or e.poll_id != poll_id or not encuesta.a_tiempo(e, ahora):
        logger.info("Voto en una encuesta que ya no cuenta (%s)", poll_id)
        return

    if not opciones:
        # Ha retirado el voto: fuera también la predicción que salió de él.
        database.quitar_prediccion(config.database_path, e.coin_id, config.vs_currency)
        texto = (
            f"Hecho, quitada tu predicción de <b>{telegram.escape(e.coin_id)}</b>. "
            "Puedes volver a votar hasta que se cierre."
        )
    else:
        valor = encuesta.predicho(e.entonces, opciones[0])
        if valor is None:
            return
        p = database.guardar_prediccion(
            config.database_path,
            prediccion.Prediccion(None, e.coin_id, ahora, e.cierre, e.entonces, valor),
            config.vs_currency,
        )
        elegida = alerts.opciones_encuesta(e, config.vs_currency)[opciones[0]]
        texto = alerts.formatear_voto_encuesta(p, elegida, config.vs_currency)
    telegram.send_message(
        config.telegram_token,
        config.telegram_chat_id,
        texto,
        sin_sonido=_sin_sonido(config),
    )


def _jugadores(config: Config) -> list[liga.Jugador]:
    """Tú y tus invitados con sus predicciones, vistos desde quien pregunta."""
    # Un invitado solo sabe de su archivo; la lista de todos está en el tuyo.
    del_dueño = config.archivo_dueño or config.database_path
    dueño = replace(config, database_path=del_dueño)
    fichas = [(None, "El anfitrión", del_dueño)]
    for n, invitado in enumerate(database.get_invitados(del_dueño), start=1):
        fichas.append(
            (
                invitado.chat_id,
                invitado.nombre or f"Invitado {n}",
                usuarios.archivo(dueño, invitado.chat_id),
            )
        )

    yo = config.telegram_chat_id if config.invitado else None
    jugadores = []
    for chat, nombre, ruta in fichas:
        try:
            suyas = database.get_predicciones(ruta, config.vs_currency)
        except database.DatabaseError as e:
            # Uno con el archivo roto no deja a los demás sin liga.
            logger.warning("La liga va sin %s: %s", chat or "el dueño", e)
            continue
        jugadores.append(liga.Jugador(nombre, chat == yo, suyas))
    return jugadores


def _liga(config: Config, argumento: str) -> str:
    try:
        semana = liga.interpretar(argumento)
    except liga.LigaError as e:
        return telegram.escape(str(e))
    jugadores = _jugadores(config)
    jornada = liga.ultima_jornada(jugadores) if semana else None
    return alerts.formatear_liga(liga.clasificar(jugadores, jornada), jornada)


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


def _tesis(config: Config, argumento: str) -> str:
    lista = database.get_tesis(config.database_path)
    if not argumento:
        return alerts.formatear_tesis(lista)
    try:
        pedido = tesis.interpretar(argumento)
    except tesis.TesisError as e:
        return telegram.escape(str(e))

    if isinstance(pedido, tesis.Quitar):
        if database.quitar_tesis(config.database_path, pedido.numero):
            return f"Hecho, quitada la {pedido.numero}."
        return "No tienes ninguna con ese número. Mira /tesis"

    if isinstance(pedido, tesis.Veredicto):
        t = next((t for t in lista if t.numero == pedido.numero), None)
        if t is None:
            return "No tienes ninguna con ese número. Mira /tesis"
        if not t.preguntada:
            return (
                f"La {t.numero} aún no toca: te pregunto el "
                f"{t.vence.astimezone():%d/%m}. Juzgarla antes es hacer trampa."
            )
        t = replace(t, acerto=pedido.acerto)
        database.guardar_tesis(config.database_path, t)
        lista = [t if x.numero == t.numero else x for x in lista]
        return alerts.formatear_tesis_juzgada(t, *tesis.marcador(lista))

    if len(tesis.pendientes(lista)) >= tesis.MAXIMO:
        return (
            f"Ya tienes {tesis.MAXIMO} esperando. Quita alguna antes: /tesis quitar 3"
        )
    precio = _precio_o_pedirlo(config, pedido.coin_id)
    if isinstance(precio, str):
        return precio
    t = tesis.Tesis(
        tesis.siguiente(lista),
        pedido.coin_id,
        pedido.texto,
        precio,
        datetime.now(timezone.utc),
        pedido.dias,
    )
    database.guardar_tesis(config.database_path, t)
    logger.info("Tesis %d de %s apuntada", t.numero, t.coin_id)
    return alerts.con_fuente(alerts.formatear_tesis_nueva(t, config.vs_currency))


def tesis_vencidas(config: Config, ahora: datetime | None = None) -> None:
    """Cuando se cumple el plazo de una /tesis, te pregunto si acertaste."""
    ahora = ahora or datetime.now(timezone.utc)
    try:
        tocan = tesis.tocan(database.get_tesis(config.database_path), ahora)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer las /tesis: %s", e)
        return
    if not tocan or _silenciado(config):
        return

    ids = list(dict.fromkeys(t.coin_id for t in tocan))
    try:
        precios = coingecko.get_prices(ids, config.vs_currency)
    except coingecko.CoinGeckoError as e:
        logger.warning("Sin precio para las /tesis: %s", e)
        return

    for t in tocan:
        precio = precios.get(t.coin_id)
        if precio is None:
            continue
        if not telegram.send_message(
            config.telegram_token,
            config.telegram_chat_id,
            alerts.con_fuente(
                alerts.formatear_tesis_vencida(t, precio, config.vs_currency)
            ),
            botones=botones.para_tesis(t.numero),
        ):
            logger.error("No se pudo preguntar por la /tesis %d", t.numero)
            continue
        # Con el precio de hoy guardado: la lista enseña cómo acabó, no cómo va.
        database.guardar_tesis(config.database_path, replace(t, final=precio))
        logger.info("/tesis %d preguntada", t.numero)


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
