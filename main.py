"""Punto de entrada: consulta precios, los guarda, compara y avisa.

Uso:
    python main.py                    una consulta y sale
    python main.py --loop             vigila en bucle
    python main.py --test             manda un mensaje de prueba a Telegram
    python main.py --status           manda un resumen de como van los precios
    python main.py --mute 2h          calla los avisos durante dos horas
    python main.py --unmute           vuelve a avisar
    python main.py --history bitcoin  muestra el historico guardado
"""

import argparse
import logging
import sys
import time
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from crypto_tracker import (
    alerts,
    botones,
    brusco,
    cartera,
    coingecko,
    comandos,
    convertir,
    cuota,
    database,
    diario,
    exportar,
    extremos,
    grafica,
    movimientos,
    periodo,
    proximo,
    puntuales,
    salud,
    semanal,
    simbolos,
    telegram,
    vigiladas,
)
from crypto_tracker.config import (
    Config,
    ConfigError,
    load_config,
    parse_duracion,
)

logger = logging.getLogger("crypto_tracker")

# Si el ciclo falla estas veces seguidas, algo va mal de verdad y paramos.
MAX_FALLOS = 10

# Con cuanto tiempo atras se compara el precio en el resumen.
HORAS_RESUMEN = 24

# Una cartera se mira a mas largo plazo que un precio suelto.
HORAS_CARTERA = 7 * 24

# Segundos que Telegram aguanta la conexion abierta esperando un mensaje.
ESPERA_TELEGRAM = 30

# Lo que escribiste con el bot apagado no se contesta: un /mute de anoche
# no pinta nada esta mañana.
ANTIGUEDAD_MAXIMA = 10 * 60

# Lo que dura un /mute a secas, el mismo que el boton de callar de los avisos.
MUTE_POR_DEFECTO = "1h"

# El del bucle en marcha, para que /bot sepa como va. None fuera de --loop.
_pulso: salud.Pulso | None = None


def configurar_logs(verbose: bool = False) -> None:
    """Deja los logs con hora y nivel, para saber que paso y cuando."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def ejecutar_ciclo(
    config: Config, estado: dict[str, str], sin_precio: set[str] | None = None
) -> tuple[dict[str, str], str | None]:
    """Un ciclo completo: consultar, guardar, comparar y avisar.

    Devuelve el estado actualizado y, si no hubo precios, el porque. Si algo
    falla, lo registra y devuelve el estado sin tocar para reintentar luego.
    sin_precio son los ids de los que ya se aviso que no existen.
    """
    config = _con_cambios(config)
    coin_ids = [w.coin_id for w in config.watchlist]
    pendientes = _puntuales(config)
    # Las de /alerta y la cartera pueden ser de criptos que no vigilas. Van en
    # la misma consulta, y asi la cartera tiene historico para su grafica.
    extra = [p.coin_id for p in (*pendientes, *config.cartera)]
    extra = [c for c in extra if c not in coin_ids and c != puntuales.CARTERA]

    try:
        precios = coingecko.get_prices(
            coin_ids + list(dict.fromkeys(extra)), config.vs_currency
        )
    except coingecko.CoinGeckoError as e:
        logger.error("No se pudieron consultar los precios: %s", e)
        return estado, str(e)

    avisar_sin_precio(
        config, coin_ids, precios, set() if sin_precio is None else sin_precio
    )

    if not precios:
        logger.warning("La consulta no devolvio ningun precio")
        return estado, "La consulta no devolvio ningun precio"

    logger.info(
        "Precios: %s",
        ", ".join(f"{c}={p}" for c, p in sorted(precios.items())),
    )

    # Lo guardado antes de esto es el pasado contra el que se miran los maximos.
    antes_de_guardar = datetime.now(timezone.utc).replace(microsecond=0)

    # Guardar no es critico: si falla el disco, aun queremos avisar.
    try:
        database.save_prices(config.database_path, precios, config.vs_currency)
    except database.DatabaseError as e:
        logger.error("No se pudo guardar en la base de datos: %s", e)

    # Si falla la purga da igual, seguimos avisando.
    if config.history_days > 0:
        try:
            database.purge_old_prices(config.database_path, config.history_days)
        except database.DatabaseError as e:
            logger.error("No se pudo purgar el historico: %s", e)

    estado = _olvidar_cambiadas(config, estado)
    avisos, estado_nuevo = alerts.revisar(precios, config.watchlist, estado)
    vigiladas = {c: p for c, p in precios.items() if c in coin_ids}
    avisos += revisar_bruscos(config, vigiladas)
    avisos += revisar_extremos(config, vigiladas, antes_de_guardar)

    # Para las de /alerta cartera, lo que vale todo junto cuenta como un precio mas.
    con_cartera = dict(precios)
    valor = cartera.valor_total(list(config.cartera), precios)
    if valor is not None:
        con_cartera[puntuales.CARTERA] = valor

    hechas = puntuales.cumplidas(pendientes, con_cartera)
    avisos += [
        alerts.Alert(
            p.coin_id,
            con_cartera[p.coin_id],
            p.objetivo,
            alerts.ALTO if p.sube else alerts.BAJO,
            puntual=True,
        )
        for p in hechas
    ]

    # Guardamos la zona de cada cripto para no repetir el aviso al reiniciar.
    try:
        database.save_state(config.database_path, estado_nuevo)
    except database.DatabaseError as e:
        logger.error("No se pudo guardar el estado de las alertas: %s", e)

    if not avisos:
        logger.info("Ningun umbral cruzado")
        return estado_nuevo, None

    # Silenciado: el estado ya se guardo, asi que al volver no llega de golpe
    # todo lo que paso mientras, solo lo que este cruzado en ese momento.
    # Las de /alerta no se borran, saltan al volver si siguen cumplidas.
    callado = _silenciado(config)
    if callado:
        logger.info(
            "Silenciado hasta las %s, no aviso de: %s",
            callado.astimezone().strftime("%H:%M"),
            ", ".join(a.coin_id for a in avisos),
        )
        return estado_nuevo, None

    avisos = [
        replace(a, variacion_24h=_variacion(config, a.coin_id, a.price)) for a in avisos
    ]

    # Todo en un mensaje: si cruzan tres a la vez, tres notificaciones
    # seguidas molestan y encima Telegram empieza a cortar el ritmo.
    texto = alerts.con_fuente(alerts.formatear_varios(avisos, config.vs_currency))
    cruzadas = ", ".join(f"{a.coin_id} {a.estado}" for a in avisos)

    if telegram.send_message(
        config.telegram_token,
        config.telegram_chat_id,
        texto,
        sin_sonido=_sin_sonido(config),
        botones=botones.para_avisos(avisos, config.vs_currency),
    ):
        logger.info("Aviso enviado (%d): %s", len(avisos), cruzadas)
        _borrar_puntuales(config, hechas)
    else:
        # El aviso se perdio, pero el estado ya cambio. No insistimos:
        # el siguiente cruce volvera a avisar. Las de /alerta siguen ahi.
        logger.error("No se pudo avisar de: %s", cruzadas)

    return estado_nuevo, None


def _con_cambios(config: Config) -> Config:
    """La config de verdad: lo que vigilas y tu cartera, el .env mas lo de Telegram."""
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
    return config


def _olvidar_cambiadas(config: Config, estado: dict[str, str]) -> dict[str, str]:
    """Si cambiaste la regla, el nivel guardado con la vieja daria avisos falsos."""
    try:
        cambiadas = database.tomar_de_cero(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudo mirar que criptos han cambiado: %s", e)
        return estado

    if cambiadas:
        logger.info("Empiezan de cero: %s", ", ".join(sorted(cambiadas)))
    return {c: v for c, v in estado.items() if c not in cambiadas}


def _puntuales(config: Config) -> list[puntuales.Puntual]:
    try:
        return database.get_puntuales(config.database_path, config.vs_currency)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer las alertas de /alerta: %s", e)
        return []


def _borrar_puntuales(config: Config, hechas: list[puntuales.Puntual]) -> None:
    for p in hechas:
        try:
            database.borrar_puntual(config.database_path, p.id)
        except database.DatabaseError as e:
            # Volvera a avisar el siguiente ciclo. Mejor repetido que perdido.
            logger.error("No se pudo borrar la alerta %d: %s", p.id, e)


def avisar_sin_precio(
    config: Config, coin_ids: list[str], precios: dict[str, float], avisadas: set[str]
) -> None:
    """Avisa una vez de los ids que CoinGecko no conoce. Si no, nunca te enteras."""
    nuevas = salud.sin_precio(coin_ids, precios, avisadas)
    if not nuevas:
        return

    texto = salud.mensaje_sin_precio(nuevas, todas=not precios)
    # Si no llega, no se apuntan: se reintenta en el siguiente ciclo.
    if _avisar_salud(config, texto):
        avisadas.update(nuevas)


def revisar_bruscos(config: Config, precios: dict[str, float]) -> list[alerts.Alert]:
    """Busca subidas o caidas fuertes dentro de la ventana de MOVIMIENTO_BRUSCO."""
    if config.brusco_porcentaje is None:
        return []

    ahora = datetime.now(timezone.utc)
    avisos = []

    for coin_id, precio in precios.items():
        desde = ahora - timedelta(minutes=config.brusco_minutos)
        try:
            # Tras un aviso solo cuenta lo que pase despues. Si no, una caida
            # del 8% avisaria en cada ciclo durante toda la hora siguiente.
            ultimo = database.ultimo_brusco(config.database_path, coin_id)
            if ultimo and ultimo > desde:
                desde = ultimo
            ventana = database.get_prices_desde(
                config.database_path, coin_id, desde, config.vs_currency
            )
        except database.DatabaseError as e:
            logger.error("No se pudo mirar el movimiento de %s: %s", coin_id, e)
            continue

        # El de ahora va aparte por si no se pudo guardar.
        aviso = brusco.revisar(
            coin_id,
            ventana + [precio],
            config.brusco_porcentaje,
            config.brusco_minutos,
        )
        if aviso is None:
            continue

        avisos.append(aviso)
        try:
            database.guardar_brusco(config.database_path, coin_id, ahora)
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar el aviso brusco de %s: %s", coin_id, e)

    return avisos


def revisar_extremos(
    config: Config, precios: dict[str, float], hasta: datetime
) -> list[alerts.Alert]:
    """Busca maximos o minimos de los ultimos MAXIMOS_MINIMOS dias."""
    if config.extremos_dias is None:
        return []

    desde = hasta - timedelta(days=config.extremos_dias)
    avisos = []
    for coin_id, precio in precios.items():
        try:
            rango = database.get_rango(
                config.database_path, coin_id, desde, hasta, config.vs_currency
            )
            aviso = extremos.revisar(
                coin_id, precio, rango, hasta, config.extremos_dias
            )
            if aviso is None:
                continue
            ultimo = database.ultimo_extremo(
                config.database_path, coin_id, aviso.estado
            )
            if not extremos.toca(ultimo, hasta):
                continue
            database.guardar_extremo(config.database_path, coin_id, aviso.estado, hasta)
        except database.DatabaseError as e:
            # Sin poder apuntarlo avisaria en cada ciclo; mejor callar este.
            logger.error("No se pudo mirar el maximo o minimo de %s: %s", coin_id, e)
            continue
        avisos.append(aviso)

    return avisos


def ejecutar_bucle(config: Config, estado: dict[str, str]) -> int:
    """Repite el ciclo cada CHECK_INTERVAL segundos hasta que se corte.

    Aguanta los fallos sueltos: si algo revienta de forma inesperada lo
    registra y sigue. Solo se rinde si falla muchas veces seguidas.
    """
    logger.info(
        "Modo bucle cada %ds. Ctrl+C para parar.",
        config.check_interval,
    )

    global _pulso
    fallos = 0
    pulso = _pulso = salud.Pulso()
    sin_precio: set[str] = set()
    offset = None

    if not telegram.set_commands(config.telegram_token, comandos.COMANDOS):
        logger.warning("No se pudo poner el menu de comandos en Telegram")
    avisar_encendido(config)

    while True:
        try:
            estado, problema = ejecutar_ciclo(config, estado, sin_precio)
            fallos = 0
            resumen_diario(config)
            resumen_semanal(config)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            # Red a la que caen los errores que no previmos. Sin esto, un
            # fallo raro a las 3 de la mañana mata el vigilante entero.
            fallos += 1
            problema = f"{type(e).__name__}: {e}"
            logger.exception("Error inesperado en el ciclo (%d seguidos)", fallos)

            if fallos >= MAX_FALLOS:
                logger.error("Demasiados fallos seguidos, paro.")
                _avisar_salud(config, salud.mensaje_parado(fallos, problema))
                return 1

        texto = pulso.fallo(problema) if problema else pulso.exito()
        if texto:
            _avisar_salud(config, texto)

        # Aqui entran tambien las de los comandos de la espera anterior.
        apuntar_consultas(config)
        offset = esperar_escuchando(config, config.check_interval, offset)


def avisar_encendido(config: Config) -> None:
    """Asi, si el servidor se reinicia o el vigia lo levanta, te enteras."""
    try:
        ultimo = database.ultimo_guardado(config.database_path)
    except database.DatabaseError as e:
        # Sin esto el aviso vale igual, solo sin decir cuanto estuvo apagado.
        logger.warning("No se pudo mirar el ultimo precio guardado: %s", e)
        ultimo = None

    _avisar_salud(
        config,
        salud.mensaje_encendido(
            len(_con_cambios(config).watchlist),
            config.check_interval,
            ultimo,
            datetime.now(timezone.utc),
        ),
    )


def apuntar_consultas(config: Config, ahora: datetime | None = None) -> None:
    """Guarda las consultas hechas a CoinGecko y avisa si se acaba la cuota."""
    hechas = coingecko.tomar_consultas()
    if not hechas:
        return

    ahora = ahora or datetime.now(timezone.utc)
    try:
        total = database.sumar_consultas(config.database_path, cuota.mes(ahora), hechas)
    except database.DatabaseError as e:
        # Se pierden estas pocas; es un contador, no la contabilidad.
        logger.warning("No se pudieron apuntar las consultas: %s", e)
        return

    umbral = cuota.umbral_cruzado(total - hechas, total)
    if umbral:
        logger.warning("Llevamos %d consultas a CoinGecko este mes", total)
        _avisar_salud(config, cuota.mensaje_aviso(total, umbral, ahora))


def esperar_escuchando(config: Config, segundos: int, offset: int | None) -> int | None:
    """Espera al siguiente ciclo contestando lo que llegue por Telegram."""
    fin = time.monotonic() + segundos

    while (queda := fin - time.monotonic()) > 0:
        espera = max(1, int(min(queda, ESPERA_TELEGRAM)))
        try:
            mensajes = telegram.get_updates(config.telegram_token, offset, espera)
        except telegram.TelegramError as e:
            logger.warning("%s", e)
            # Sin esto, sin red se pondria a preguntar sin parar.
            time.sleep(min(queda, ESPERA_TELEGRAM))
            continue

        for update in mensajes:
            # Se mueve antes de contestar: si un mensaje revienta, no queremos
            # que vuelva a llegar una y otra vez.
            offset = update["update_id"] + 1
            try:
                if "callback_query" in update:
                    atender_boton(config, update["callback_query"])
                else:
                    atender(config, update.get("message") or {})
            except Exception:
                logger.exception("Error contestando un comando")

    return offset


def atender(config: Config, mensaje: dict) -> None:
    """Contesta un mensaje de Telegram, si viene de tu chat."""
    chat = str(mensaje.get("chat", {}).get("id", ""))
    if chat != config.telegram_chat_id:
        # Cualquiera puede dar con el bot y escribirle; solo te hace caso a ti.
        logger.warning("Mensaje de un chat que no es el tuyo (%s), lo ignoro", chat)
        return

    texto = mensaje.get("text") or ""
    if time.time() - mensaje.get("date", 0) > ANTIGUEDAD_MAXIMA:
        logger.info("Comando antiguo, no lo contesto: %s", texto)
        return

    logger.info("Comando recibido: %s", texto)
    contestar(config, texto)


def atender_boton(config: Config, boton: dict) -> None:
    """Un boton de debajo de un aviso. Lleva dentro el comando que hace."""
    # Hay que contestarlo aunque no sea tuyo, o se queda dando vueltas.
    telegram.answer_callback(config.telegram_token, boton.get("id", ""))

    chat = str((boton.get("message") or {}).get("chat", {}).get("id", ""))
    if chat != config.telegram_chat_id:
        logger.warning("Boton de un chat que no es el tuyo (%s), lo ignoro", chat)
        return

    # Sin mirar la antigüedad: un aviso de ayer sigue teniendo sus botones.
    texto = boton.get("data") or ""
    logger.info("Boton pulsado: %s", texto)
    contestar(config, texto)


def contestar(config: Config, texto: str) -> None:
    """Hace el comando y manda la respuesta, con imagen si la lleva."""
    orden = comandos.interpretar(texto)

    try:
        respuesta = responder(config, *orden) if orden else comandos.NO_ENTIENDO
    except database.DatabaseError as e:
        logger.error("Error de la base de datos contestando '%s': %s", texto, e)
        respuesta = "⚠️ Algo ha fallado con la base de datos. Mira el log."

    if isinstance(respuesta, comandos.Foto):
        if telegram.send_photo(
            config.telegram_token,
            config.telegram_chat_id,
            respuesta.png,
            respuesta.pie,
            botones=respuesta.botones,
        ):
            return
        if respuesta.botones:
            respuesta = comandos.ConBotones(respuesta.texto, respuesta.botones)
        else:
            respuesta = respuesta.texto

    if isinstance(respuesta, comandos.Archivo):
        if telegram.send_document(
            config.telegram_token,
            config.telegram_chat_id,
            respuesta.contenido,
            respuesta.nombre,
            respuesta.pie,
        ):
            return
        respuesta = respuesta.texto

    teclado = None
    if isinstance(respuesta, comandos.ConBotones):
        respuesta, teclado = respuesta.texto, respuesta.botones

    telegram.send_message(
        config.telegram_token, config.telegram_chat_id, respuesta, botones=teclado
    )


def responder(
    config: Config, nombre: str, argumento: str
) -> str | comandos.Foto | comandos.Archivo | comandos.ConBotones:
    """El texto con el que se contesta a cada comando."""
    if nombre == "ayuda":
        return comandos.AYUDA

    if nombre == "status":
        texto = montar_resumen(config)
        if texto is None:
            return "No he podido consultar los precios. Prueba en un rato."
        return comandos.ConBotones(texto, botones.actualizar("/status"))

    if nombre == "mute":
        if not argumento:
            # A secas, si ya estaba callado, mejor decirlo que alargarlo sin querer.
            estaba = database.silenciado_hasta(config.database_path)
            if estaba:
                cuando = estaba.astimezone()
                return (
                    f"🔕 Ya estoy callado hasta las {cuando:%H:%M del %d/%m}.\n"
                    "Para volver antes: /unmute · para cambiarlo: /mute 2h"
                )
            argumento = MUTE_POR_DEFECTO
        try:
            minutos = parse_duracion(argumento)
        except ConfigError as e:
            return str(e)
        hasta = datetime.now(timezone.utc) + timedelta(minutes=minutos)
        database.silenciar_hasta(config.database_path, hasta)
        return (
            f"🔕 Callado hasta las {hasta.astimezone():%H:%M del %d/%m}.\n"
            "Para volver antes: /unmute"
        )

    if nombre == "unmute":
        estaba = database.silenciado_hasta(config.database_path)
        database.silenciar_hasta(config.database_path, None)
        return "🔔 Vuelvo a avisar." if estaba else "No estaba callado."

    if nombre == "cartera":
        config = _con_cambios(config)
        if not config.cartera:
            return (
                "No tienes cartera puesta. Apunta lo que tienes con "
                "/compra bitcoin 0.016 1000, o añade al .env algo como:\n"
                "<code>PORTFOLIO=bitcoin:0.016:1000</code>"
            )
        return _cartera(config, argumento)

    if nombre == "compra":
        return _comprar(config, argumento)

    if nombre == "venta":
        return _vender(config, argumento)

    if nombre == "historico":
        return _historico(config, argumento)

    if nombre == "alerta":
        return _crear_alerta(config, argumento)

    if nombre == "vigilar":
        return _vigilar(config, argumento) if argumento else _lista_vigiladas(config)

    if nombre == "dejar":
        return _dejar(config, simbolos.a_id(argumento))

    if nombre == "alertas":
        pendientes = database.get_puntuales(config.database_path, config.vs_currency)
        precios = _precios_alertas(config, pendientes)
        texto = alerts.formatear_puntuales(pendientes, config.vs_currency, precios)
        if precios:
            texto = alerts.con_fuente(texto)
        if not pendientes:
            return texto
        return comandos.ConBotones(texto, botones.para_alertas(pendientes))

    if nombre == "quitar":
        if argumento.lower() == "todas":
            cuantas = database.borrar_puntuales(
                config.database_path, config.vs_currency
            )
            if not cuantas:
                return "No tenías ninguna alerta puesta."
            if cuantas == 1:
                return "🗑 Alerta quitada."
            return f"🗑 {cuantas} alertas quitadas."
        try:
            numeros = puntuales.numeros(argumento)
        except puntuales.PuntualError:
            return (
                "¿Cuál? Mira el número con /alertas y luego, por ejemplo, /quitar 3 "
                "o /quitar 2 5. Para quitarlas todas: /quitar todas"
            )
        quitadas = [
            n for n in numeros if database.borrar_puntual(config.database_path, n)
        ]
        no_estaban = [n for n in numeros if n not in quitadas]
        return alerts.formatear_quitadas(quitadas, no_estaban)

    if nombre == "consultas":
        apuntar_consultas(config)
        ahora = datetime.now(timezone.utc)
        total = database.get_consultas(config.database_path, cuota.mes(ahora))
        return cuota.mensaje_estado(total, ahora)

    if nombre == "bot":
        if _pulso is None:
            return "Esto solo lo sé con el bot vigilando (--loop)."
        return salud.mensaje_bot(
            _pulso,
            datetime.now(timezone.utc),
            len(_con_cambios(config).watchlist),
            len(database.get_puntuales(config.database_path, config.vs_currency)),
            _silenciado(config),
        )

    if nombre == "precio":
        return _precio(config, argumento)

    if nombre == "convertir":
        return _convertir(config, argumento)

    if nombre == "exportar":
        return _exportar(config, argumento)

    if nombre == "buscar":
        if not argumento:
            return "¿Qué busco? Por ejemplo: /buscar btc"
        try:
            resultados = coingecko.buscar(argumento)
        except coingecko.CoinGeckoError as e:
            return f"No he podido buscar ahora mismo: {telegram.escape(str(e))}"
        if not resultados:
            return alerts.formatear_busqueda(argumento, resultados)
        return alerts.con_fuente(alerts.formatear_busqueda(argumento, resultados))

    return comandos.NO_ENTIENDO


def _lista_vigiladas(config: Config) -> str:
    cambios = database.get_cambios(config.database_path)
    desde_telegram = {c for c, regla in cambios.items() if regla is not None}
    return alerts.formatear_vigiladas(
        _con_cambios(config).watchlist, config.vs_currency, desde_telegram
    )


def _vigilar(config: Config, argumento: str) -> str:
    try:
        watch, regla = vigiladas.interpretar(argumento)
    except vigiladas.VigilarError as e:
        return telegram.escape(str(e))

    nombre = telegram.escape(watch.coin_id.replace("-", " ").title())
    ya_estaba = watch.coin_id in {w.coin_id for w in _con_cambios(config).watchlist}

    # Si es nueva, que exista. Si no, nos enterariamos en el siguiente ciclo.
    if not ya_estaba:
        try:
            precios = coingecko.get_prices([watch.coin_id], config.vs_currency)
        except coingecko.CoinGeckoError as e:
            return (
                f"No he podido comprobar el id ahora mismo: {telegram.escape(str(e))}"
            )
        if watch.coin_id not in precios:
            return (
                f"No encuentro <b>{telegram.escape(watch.coin_id)}</b> en CoinGecko. "
                f"Prueba con /buscar {telegram.escape(watch.coin_id)}"
            )

    database.guardar_cambio(config.database_path, watch.coin_id, regla)
    logger.info("Watchlist: %s pasa a %s", watch.coin_id, regla)
    texto = f"👀 Vigilo <b>{nombre}</b>: {alerts.describir(watch, config.vs_currency)}."
    # Los rangos avisan nada mas empezar si ya esta fuera; los otros no.
    if watch.percent is not None or watch.step is not None:
        texto += "\nEmpieza de cero, así que el primer ciclo solo apunta dónde está."
    return texto


def _dejar(config: Config, coin_id: str) -> str:
    if not coin_id:
        return "¿Cuál? Por ejemplo: /dejar solana"

    actuales = [w.coin_id for w in _con_cambios(config).watchlist]
    if coin_id not in actuales:
        return f"No estoy vigilando <b>{telegram.escape(coin_id)}</b>. Mira /vigilar"
    if len(actuales) == 1:
        return (
            "Es la única que vigilo. Si la quito no te avisaría de nada. "
            "Añade otra antes con /vigilar."
        )

    database.guardar_cambio(config.database_path, coin_id, None)
    logger.info("Watchlist: deja de vigilar %s", coin_id)
    nombre = telegram.escape(coin_id.replace("-", " ").title())
    return f"👋 Dejo de vigilar <b>{nombre}</b>."


def _comprar(config: Config, argumento: str) -> str:
    try:
        coin_id, cantidad, coste = movimientos.interpretar_compra(argumento)
    except movimientos.MovimientoError as e:
        return telegram.escape(str(e))

    antes = movimientos.buscar(_con_cambios(config).cartera, coin_id)
    # Sin coste hace falta el precio de ahora; si es nueva, de paso vemos que existe.
    if coste is None or antes is None:
        try:
            precios = coingecko.get_prices([coin_id], config.vs_currency)
        except coingecko.CoinGeckoError as e:
            return f"No he podido consultar el precio: {telegram.escape(str(e))}"
        if coin_id not in precios:
            return (
                f"No encuentro <b>{telegram.escape(coin_id)}</b> en CoinGecko. "
                f"Prueba con /buscar {telegram.escape(coin_id)}"
            )
        if coste is None:
            coste = cantidad * precios[coin_id]

    ahora = movimientos.comprar(antes, coin_id, cantidad, coste)
    database.guardar_posicion(config.database_path, coin_id, ahora)
    logger.info("Cartera: compra %s de %s por %s", cantidad, coin_id, coste)
    return alerts.formatear_compra(cantidad, coste, ahora, config.vs_currency)


def _vender(config: Config, argumento: str) -> str:
    try:
        coin_id, cantidad = movimientos.interpretar_venta(argumento)
        antes = movimientos.buscar(_con_cambios(config).cartera, coin_id)
        queda = movimientos.vender(antes, coin_id, cantidad)
    except movimientos.MovimientoError as e:
        return telegram.escape(str(e))

    vendido = antes.cantidad if cantidad is None else cantidad
    database.guardar_posicion(config.database_path, coin_id, queda)
    logger.info("Cartera: vende %s de %s", vendido, coin_id)
    return alerts.formatear_venta(coin_id, vendido, queda, config.vs_currency)


def _crear_alerta(config: Config, argumento: str) -> str:
    try:
        relativa = puntuales.interpretar_relativa(argumento)
        if relativa:
            coin_id, porcentaje = relativa
        else:
            coin_id, objetivo = puntuales.interpretar(argumento)
    except puntuales.PuntualError as e:
        return telegram.escape(str(e))

    es_cartera = coin_id == puntuales.CARTERA
    if es_cartera and not _con_cambios(config).cartera:
        return "No tienes cartera. Apunta lo que tienes con /compra bitcoin 0.016 1000"

    # Hace falta el precio de ahora para saber si esperar a que suba o a que
    # baje. Y de paso se comprueba que el id existe.
    try:
        if es_cartera:
            precio = _valor_cartera(config)
        else:
            precio = coingecko.get_prices([coin_id], config.vs_currency).get(coin_id)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirar el precio ahora mismo: {telegram.escape(str(e))}"

    if precio is None and es_cartera:
        return (
            "Ahora mismo no tengo el precio de todo lo que tienes. Prueba en un rato."
        )
    if precio is None:
        return (
            f"No encuentro <b>{telegram.escape(coin_id)}</b> en CoinGecko. "
            f"Prueba con /buscar {telegram.escape(coin_id)}"
        )

    if relativa:
        # El precio se fija ahora: "+10%" es desde lo que vale en este momento.
        objetivo = puntuales.objetivo_relativo(precio, porcentaje)
        sube = porcentaje > 0
    else:
        try:
            sube = puntuales.sube(objetivo, precio)
        except puntuales.PuntualError as e:
            return telegram.escape(str(e))

    alerta = database.crear_puntual(
        config.database_path, coin_id, objetivo, sube, config.vs_currency
    )
    logger.info("Alerta %d creada: %s a %s", alerta.id, coin_id, objetivo)
    return alerts.con_fuente(
        alerts.formatear_puntual(alerta, precio, config.vs_currency)
    )


def _precio(config: Config, argumento: str) -> str:
    coin_ids = simbolos.varias(argumento)
    if not coin_ids:
        return "¿De cuál? Por ejemplo: /precio solana o /precio btc eth sol"
    if len(coin_ids) > simbolos.MAX_VARIAS:
        return f"Como mucho {simbolos.MAX_VARIAS} a la vez."

    try:
        precios = coingecko.get_prices(coin_ids, config.vs_currency)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirar el precio ahora mismo: {telegram.escape(str(e))}"

    lineas = [
        (c, precios[c], _variacion(config, c, precios[c]))
        for c in coin_ids
        if c in precios
    ]
    faltan = [c for c in coin_ids if c not in precios]
    if not lineas:
        return alerts.formatear_no_encuentro(faltan)

    if len(coin_ids) == 1:
        return alerts.con_fuente(
            alerts.formatear_precio(*lineas[0], config.vs_currency)
        )
    return alerts.con_fuente(
        alerts.formatear_precios(lineas, faltan, config.vs_currency)
    )


def _convertir(config: Config, argumento: str) -> str:
    try:
        conversion = convertir.interpretar(argumento, config.vs_currency)
    except convertir.ConvertirError as e:
        return telegram.escape(str(e))

    coin_id = conversion.coin_id
    try:
        precio = coingecko.get_prices([coin_id], config.vs_currency).get(coin_id)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirar el precio ahora mismo: {telegram.escape(str(e))}"
    if not precio:
        return (
            f"No encuentro <b>{telegram.escape(coin_id)}</b> en CoinGecko. "
            f"Prueba con /buscar {telegram.escape(coin_id)}"
        )

    resultado = conversion.resultado(precio)
    dinero, cripto = (
        (conversion.cantidad, resultado)
        if conversion.desde_dinero
        else (resultado, conversion.cantidad)
    )
    return alerts.con_fuente(
        alerts.formatear_conversion(
            dinero, cripto, coin_id, precio, conversion.desde_dinero, config.vs_currency
        )
    )


def _exportar(config: Config, argumento: str) -> str | comandos.Archivo:
    try:
        coin_id, horas = exportar.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))

    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    nombre = telegram.escape(coin_id)
    if not serie:
        return (
            f"No tengo precios de <b>{nombre}</b> ({periodo.nombre(horas)}). "
            f"Si no das con el nombre, prueba con /buscar {nombre}"
        )

    pie = f"📄 {len(serie)} precios de <b>{nombre}</b>, {periodo.nombre(horas)}"
    primero = serie[0][0]
    if periodo.falta_principio(primero, datetime.now(timezone.utc), horas):
        pie += (
            f"\n<i>Solo los tengo desde el {primero.astimezone():%d/%m a las %H:%M}</i>"
        )

    return comandos.Archivo(
        exportar.a_csv(serie, config.vs_currency),
        exportar.nombre_archivo(coin_id, horas, date.today()),
        alerts.con_fuente(pie),
        "No he podido mandarte el archivo. Prueba en un rato.",
    )


def _precios_alertas(
    config: Config, pendientes: list[puntuales.Puntual]
) -> dict[str, float]:
    """Los precios de ahora para /alertas, la cartera incluida. Todo en una consulta."""
    if not pendientes:
        return {}

    posiciones = list(_con_cambios(config).cartera)
    ids = [p.coin_id for p in pendientes if p.coin_id != puntuales.CARTERA]
    if any(p.coin_id == puntuales.CARTERA for p in pendientes):
        ids += [p.coin_id for p in posiciones]

    try:
        precios = coingecko.get_prices(list(dict.fromkeys(ids)), config.vs_currency)
    except coingecko.CoinGeckoError as e:
        # La lista vale igual sin lo que falta; no merece un error.
        logger.warning("Mando /alertas sin precios: %s", e)
        return {}

    valor = cartera.valor_total(posiciones, precios)
    if valor is not None:
        precios[puntuales.CARTERA] = valor
    return precios


def _valor_cartera(config: Config) -> float | None:
    posiciones = list(_con_cambios(config).cartera)
    precios = coingecko.get_prices([p.coin_id for p in posiciones], config.vs_currency)
    return cartera.valor_total(posiciones, precios)


def _historico(config: Config, argumento: str) -> str | comandos.Foto:
    try:
        coin_id, horas = periodo.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))

    if not coin_id:
        # A secas, la primera que vigilas: suele ser la que mas te importa.
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return "¿De cuál? Por ejemplo: /historico bitcoin o /historico bitcoin 7d"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    precios = [precio for _, precio in serie]
    mias = {w.coin_id for w in _con_cambios(config).watchlist}
    if len(precios) < 2 and coin_id in mias:
        # Recien instalado: el id esta bien, lo que falta es tiempo.
        return (
            f"Aún tengo pocos precios de <b>{telegram.escape(coin_id)}</b>. "
            "Vuelve a preguntar dentro de un rato."
        )
    if len(precios) < 2:
        return (
            f"No tengo precios de <b>{telegram.escape(coin_id)}</b> "
            f"({periodo.nombre(horas)}). Si no das con el nombre, prueba con "
            f"/buscar {telegram.escape(coin_id)}"
        )

    primero = serie[0][0]
    desde = (
        primero
        if periodo.falta_principio(primero, datetime.now(timezone.utc), horas)
        else None
    )

    def mensaje(con_linea: bool) -> str:
        return alerts.con_fuente(
            alerts.formatear_historico(
                coin_id, precios, config.vs_currency, horas, con_linea, desde
            )
        )

    try:
        png = grafica.dibujar(coin_id, serie, config.vs_currency, horas)
    except Exception as e:
        # Sin imagen no pasa nada: el texto ya lleva lo importante.
        logger.warning("Mando /historico sin imagen: %s", e)
        return mensaje(con_linea=True)

    return comandos.Foto(png, mensaje(con_linea=False), mensaje(con_linea=True))


def resumen_diario(config: Config, ahora: datetime | None = None) -> None:
    """Manda el resumen del dia si toca. Si falla, lo reintenta el siguiente ciclo."""
    if config.resumen_diario is None:
        return

    ahora = ahora or datetime.now().astimezone()
    try:
        ultimo = database.ultimo_resumen(config.database_path)
    except database.DatabaseError as e:
        # Sin saber si ya se mando, mejor no arriesgarse a mandarlo cada ciclo.
        logger.error("No se pudo leer el ultimo resumen: %s", e)
        return

    if not diario.toca_resumen(ahora, config.resumen_diario, ultimo):
        return

    if _silenciado(config):
        logger.info("Toca el resumen diario, pero esta silenciado")
        return

    texto = montar_resumen(config, titulo="☀️ <b>Tu resumen del día</b>")
    if texto is None:
        return

    if not telegram.send_message(
        config.telegram_token,
        config.telegram_chat_id,
        texto,
        sin_sonido=_sin_sonido(config),
    ):
        logger.error("No se pudo enviar el resumen diario, lo reintento luego")
        return

    logger.info("Resumen diario enviado")
    try:
        database.guardar_resumen(config.database_path, ahora.date())
    except database.DatabaseError as e:
        logger.error("No se pudo apuntar el resumen, puede que llegue repetido: %s", e)


def resumen_semanal(config: Config, ahora: datetime | None = None) -> None:
    """Los domingos, a la hora del diario, como le ha ido a la cartera."""
    config = _con_cambios(config)
    if config.resumen_diario is None or not config.cartera:
        return

    ahora = ahora or datetime.now().astimezone()
    try:
        ultimo = database.ultimo_resumen(config.database_path, database.ULTIMO_SEMANAL)
    except database.DatabaseError as e:
        logger.error("No se pudo leer el ultimo resumen semanal: %s", e)
        return

    if not semanal.toca(ahora, config.resumen_diario, ultimo) or _silenciado(config):
        return

    # Con lo ya guardado: el ciclo de justo antes acaba de apuntar los precios
    # de ahora, asi que no hace falta gastar otra consulta.
    posiciones = list(config.cartera)
    try:
        filas = database.get_series(
            config.database_path,
            [p.coin_id for p in posiciones],
            semanal.HORAS,
            config.vs_currency,
        )
    except database.DatabaseError as e:
        logger.error("No se pudieron leer los precios de la semana: %s", e)
        return
    semana = semanal.semana(posiciones, filas)
    if semana is None:
        logger.info("Toca el resumen semanal, pero aun no hay precios de la semana")
    elif not _mandar_semana(config, semana):
        logger.error("No se pudo enviar el resumen semanal, lo reintento luego")
        return
    else:
        logger.info("Resumen semanal enviado")

    try:
        database.guardar_resumen(
            config.database_path, ahora.date(), database.ULTIMO_SEMANAL
        )
    except database.DatabaseError as e:
        logger.error("No se pudo apuntar el resumen semanal: %s", e)


def _mandar_semana(config: Config, semana: semanal.Semana) -> bool:
    primero = semana.serie[0][0]
    # Contra la hora de verdad, que es con la que se leyeron los precios.
    ahora = datetime.now(timezone.utc)
    desde = primero if periodo.falta_principio(primero, ahora, semanal.HORAS) else None
    texto = alerts.con_fuente(
        alerts.formatear_semana(semana, config.vs_currency, desde)
    )
    sin_sonido = _sin_sonido(config)

    invertidos = [p.invertido for p in config.cartera]
    invertido = None if None in invertidos else sum(invertidos)
    try:
        png = grafica.dibujar(
            "cartera",
            semana.serie,
            config.vs_currency,
            semanal.HORAS,
            titulo="Tu semana",
            invertido=invertido,
        )
    except Exception as e:
        logger.warning("Mando el resumen semanal sin imagen: %s", e)
    else:
        if telegram.send_photo(
            config.telegram_token,
            config.telegram_chat_id,
            png,
            texto,
            sin_sonido=sin_sonido,
        ):
            return True

    return telegram.send_message(
        config.telegram_token, config.telegram_chat_id, texto, sin_sonido=sin_sonido
    )


def _avisar_salud(config: Config, texto: str) -> bool:
    """Manda los avisos de caida y vuelta. No se callan con --mute."""
    if telegram.send_message(
        config.telegram_token,
        config.telegram_chat_id,
        texto,
        sin_sonido=_sin_sonido(config),
    ):
        logger.info("Aviso de estado enviado")
        return True

    logger.error("No se pudo mandar el aviso de estado")
    return False


def mensaje_de_prueba(config: Config) -> int:
    """Comprueba que el token y el chat_id son correctos."""
    logger.info("Enviando mensaje de prueba...")
    ok = telegram.send_message(
        config.telegram_token,
        config.telegram_chat_id,
        "✅ <b>CryptoPriceTracker</b>\nSi lees esto, la configuracion funciona.",
    )
    if ok:
        logger.info("Mensaje enviado, revisa tu Telegram")
        return 0

    logger.error("No se pudo enviar. Revisa el token y el chat_id del .env")
    return 1


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


def silenciar(config: Config, duracion: str) -> int:
    """Calla los avisos durante el tiempo que se pida."""
    try:
        minutos = parse_duracion(duracion)
    except ConfigError as e:
        logger.error("%s", e)
        return 1

    hasta = datetime.now(timezone.utc) + timedelta(minutes=minutos)

    try:
        database.silenciar_hasta(config.database_path, hasta)
    except database.DatabaseError as e:
        logger.error("No se pudo guardar el silencio: %s", e)
        return 1

    logger.info(
        "Callado hasta las %s. Para volver antes: --unmute",
        hasta.astimezone().strftime("%H:%M del %d/%m"),
    )
    return 0


def quitar_silencio(config: Config) -> int:
    """Vuelve a avisar."""
    try:
        estaba = database.silenciado_hasta(config.database_path)
        database.silenciar_hasta(config.database_path, None)
    except database.DatabaseError as e:
        logger.error("No se pudo quitar el silencio: %s", e)
        return 1

    if estaba:
        logger.info("Vuelvo a avisar")
    else:
        logger.info("No estaba silenciado")
    return 0


def enviar_resumen(config: Config) -> int:
    """Consulta los precios de ahora y manda un resumen por Telegram."""
    texto = montar_resumen(config)
    if texto is None:
        return 1

    if telegram.send_message(config.telegram_token, config.telegram_chat_id, texto):
        logger.info("Resumen enviado")
        return 0

    logger.error("No se pudo enviar el resumen")
    return 1


def montar_resumen(config: Config, titulo: str | None = None) -> str | None:
    """El texto del resumen con los precios de ahora. None si no hay precios."""
    config = _con_cambios(config)
    coin_ids = [w.coin_id for w in config.watchlist]
    # Lo de la cartera puede no estar en la lista de vigiladas, pero tambien
    # necesita precio. Una sola consulta para todo.
    extra = [p.coin_id for p in config.cartera if p.coin_id not in coin_ids]

    precios = _consultar(config, coin_ids + extra)
    if precios is None:
        return None

    lineas = []
    for coin_id in coin_ids:
        precio = precios.get(coin_id)
        if precio is None:
            continue
        lineas.append((coin_id, precio, _variacion(config, coin_id, precio)))

    proximos = _proximos(config, precios)
    if titulo:
        texto = alerts.formatear_resumen(
            lineas, config.vs_currency, titulo, proximos=proximos
        )
    else:
        texto = alerts.formatear_resumen(lineas, config.vs_currency, proximos=proximos)

    if config.cartera:
        texto += "\n\n" + _bloque_cartera(config, precios)

    return alerts.con_fuente(texto)


def _proximos(
    config: Config, precios: dict[str, float]
) -> dict[str, tuple[float | None, float | None]]:
    """Donde saltaria el siguiente aviso de cada una, segun el estado guardado."""
    try:
        estado = database.load_state(config.database_path)
    except database.DatabaseError as e:
        # Sin esto el resumen sigue valiendo, solo sin la linea de debajo.
        logger.warning("No se pudo leer el estado para el resumen: %s", e)
        return {}

    return {
        w.coin_id: proximo.objetivos(w, estado.get(w.coin_id), precios[w.coin_id])
        for w in config.watchlist
        if w.coin_id in precios
    }


def _cartera(
    config: Config, argumento: str
) -> str | comandos.Foto | comandos.ConBotones:
    """/cartera con la grafica de lo que ha valido. Sin datos, solo el texto."""
    try:
        horas = periodo.leer(argumento) if argumento else HORAS_CARTERA
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))

    texto = montar_cartera(config)
    if texto is None:
        return "No he podido consultar los precios. Prueba en un rato."
    # Con el mismo tramo: si pediste 30d, actualizar no te devuelve a 7d.
    teclado = botones.actualizar(f"/cartera {argumento}".strip())

    filas = database.get_series(
        config.database_path,
        [p.coin_id for p in config.cartera],
        horas,
        config.vs_currency,
    )
    serie = cartera.serie_valor(list(config.cartera), filas)
    if len(serie) < 2:
        return comandos.ConBotones(texto, teclado)

    # Si de alguna no sabes lo que costo, la linea mentiria: mejor sin ella.
    invertidos = [p.invertido for p in config.cartera]
    invertido = None if None in invertidos else sum(invertidos)
    try:
        png = grafica.dibujar(
            "cartera",
            serie,
            config.vs_currency,
            horas,
            titulo="Tu cartera",
            invertido=invertido,
        )
    except Exception as e:
        logger.warning("Mando /cartera sin imagen: %s", e)
        return comandos.ConBotones(texto, teclado)

    return comandos.Foto(png, texto, texto, teclado)


def montar_cartera(config: Config) -> str | None:
    """Solo la cartera, sin el resto del resumen. None si no hay precios."""
    precios = _consultar(config, [p.coin_id for p in config.cartera])
    if precios is None:
        return None
    return alerts.con_fuente(_bloque_cartera(config, precios))


def _bloque_cartera(config: Config, precios: dict[str, float]) -> str:
    valores, faltan = cartera.valorar(list(config.cartera), precios)
    return alerts.formatear_cartera(
        valores, cartera.total(valores), faltan, config.vs_currency
    )


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


def mostrar_historico(config: Config, coin_id: str, limite: int = 20) -> int:
    """Imprime los ultimos precios guardados de una cripto."""
    coin_id = coin_id.strip().lower()

    try:
        filas = database.get_history(config.database_path, coin_id, limite)
    except database.DatabaseError as e:
        logger.error("No se pudo leer el historico: %s", e)
        return 1

    if not filas:
        logger.warning(
            "No hay precios guardados de '%s'. Ejecuta el programa al menos "
            "una vez, y revisa que el id sea el de CoinGecko (bitcoin, no BTC).",
            coin_id,
        )
        return 1

    print(f"\nUltimos {len(filas)} precios de {coin_id}:\n")
    for fila in filas:
        # de 2026-08-28T10:30:00+00:00 a algo legible
        fecha = fila["created_at"].replace("T", " ")[:19]
        print(f"  {fecha}  {fila['price']:>14,.4f} {fila['currency'].upper()}")

    # solo mezclamos precios de la misma moneda, si no salen cuentas falsas
    misma = [f["price"] for f in filas if f["currency"] == config.vs_currency]
    _imprimir_resumen(misma, config.vs_currency)

    print()
    return 0


def _imprimir_resumen(precios: list[float], currency: str) -> None:
    """Maximo, minimo, media y variacion del tramo que se acaba de listar."""
    if len(precios) < 2:
        return

    moneda = currency.upper()
    print()
    # al reves: el grafico se lee de izquierda a derecha, del mas viejo al de ahora
    print(f"  {alerts.sparkline(list(reversed(precios)))}")
    print()
    print(f"  Maximo  {max(precios):>14,.4f} {moneda}")
    print(f"  Minimo  {min(precios):>14,.4f} {moneda}")
    print(f"  Media   {sum(precios) / len(precios):>14,.4f} {moneda}")

    # las filas vienen de la mas nueva a la mas vieja
    primero, ultimo = precios[-1], precios[0]
    if primero:
        variacion = (ultimo - primero) / primero * 100
        print(f"  Variacion en el tramo mostrado: {variacion:+.2f}%")


def buscar_id(texto: str) -> int:
    """Imprime los ids de CoinGecko que encajan con lo que buscas."""
    try:
        resultados = coingecko.buscar(texto)
    except coingecko.CoinGeckoError as e:
        logger.error("No se pudo buscar: %s", e)
        return 1

    if not resultados:
        print(f"\nNo encuentro nada con '{texto}' en CoinGecko.\n")
        return 1

    print(f"\nResultados para '{texto}':\n")
    for m in resultados:
        rango = f"#{m['market_cap_rank']}" if m.get("market_cap_rank") else ""
        nombre = f"{m.get('name', '')} ({str(m.get('symbol', '')).upper()})"
        print(f"  {m['id']:<28} {nombre:<32} {rango}")

    print(f"\nEn WATCHLIST va el id, por ejemplo: {resultados[0]['id']}:%5\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Notificador de precios de cripto")
    parser.add_argument(
        "--test", action="store_true", help="manda un mensaje de prueba y sale"
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="vigila en bucle cada CHECK_INTERVAL segundos",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="manda un resumen de como van los precios y sale",
    )
    parser.add_argument(
        "--mute",
        metavar="TIEMPO",
        help="calla los avisos un rato (30m, 2h, 1d) y sale",
    )
    parser.add_argument("--unmute", action="store_true", help="vuelve a avisar y sale")
    parser.add_argument(
        "--history",
        metavar="CRIPTO",
        help="muestra el historico guardado de una cripto y sale",
    )
    parser.add_argument(
        "--buscar",
        metavar="TEXTO",
        help="busca el id de CoinGecko de una cripto (ej: btc) y sale",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="logs detallados")
    args = parser.parse_args()

    configurar_logs(args.verbose)

    # Antes de leer el .env: sirve justo para rellenarlo la primera vez.
    if args.buscar:
        return buscar_id(args.buscar)

    try:
        config = load_config()
    except ConfigError as e:
        logger.error("%s", e)
        return 1

    if args.test:
        return mensaje_de_prueba(config)

    try:
        database.init_db(config.database_path)
    except database.DatabaseError as e:
        logger.error("%s", e)
        return 1

    if args.history:
        return mostrar_historico(config, args.history)

    if args.mute:
        return silenciar(config, args.mute)

    if args.unmute:
        return quitar_silencio(config)

    if args.status:
        resultado = enviar_resumen(config)
        apuntar_consultas(config)
        return resultado

    # Recuperamos en que zona quedo cada cripto la ultima vez, asi no
    # repetimos avisos ya mandados aunque el programa se haya reiniciado.
    try:
        estado = database.load_state(config.database_path)
    except database.DatabaseError as e:
        logger.warning("No se pudo leer el estado anterior: %s", e)
        estado = {}

    logger.info(
        "Vigilando %d criptos en %s",
        len(_con_cambios(config).watchlist),
        config.vs_currency,
    )

    if args.loop:
        return ejecutar_bucle(config, estado)

    ejecutar_ciclo(config, estado)
    apuntar_consultas(config)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # Ctrl+C es una salida normal, no un error: nada de traceback.
        logger.info("Parado por el usuario")
        sys.exit(0)
