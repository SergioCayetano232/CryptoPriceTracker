"""Los resúmenes: el del día, la semana, el mes y el año, y /status."""

import logging
import math
import time
from datetime import date, datetime, timedelta, timezone

from .. import cartera, miedo, movimientos
from ..avisos import alerts, diario, envivo, proximo, puntuales
from ..hacienda import aviso_renta, compensar, impuestos
from ..informes import (
    aniversario,
    anual,
    grafica,
    mensual,
    mes,
    panel,
    resumenia,
    semanal,
    tarjeta_anual,
)
from ..nucleo import backup, botones, comandos, database, periodo, telegram
from ..nucleo.config import Config
from .base import (
    SIN_CARTERA,
    Respuesta,
    _con_cambios,
    _consultar,
    _puntuales,
    _silenciado,
    _sin_sonido,
    _variacion,
)
from .cartera import (
    _bloque_cartera,
    _plan_compensar,
)

logger = logging.getLogger("crypto_tracker")

TITULO_DIARIO = "☀️ <b>Tu resumen del día</b>"


def _comando_status(config: Config, argumento: str) -> Respuesta:
    texto = montar_resumen(config)
    if texto is None:
        return "No he podido consultar los precios. Prueba en un rato."
    return comandos.ConBotones(texto, botones.actualizar("/status"))


def _comando_resumen(config: Config, argumento: str) -> Respuesta:
    # No lo apunto como enviado: el de las 9 tiene que llegar igual.
    texto = montar_resumen(
        config,
        titulo=TITULO_DIARIO,
        pie=_linea_miedo(),
        con_cerca=True,
        aniversarios=date.today(),
    )
    if texto is None:
        return "No he podido consultar los precios. Prueba en un rato."
    return comandos.ConBotones(texto, botones.actualizar("/resumen"))


def _texto_envivo(config: Config, ahora: datetime) -> str | None:
    """Lo de /envivo con lo último guardado. None si aún no hay precios."""
    config = _con_cambios(config)
    vigiladas = [w.coin_id for w in config.watchlist]
    suyas = [p.coin_id for p in config.cartera if p.coin_id not in vigiladas]
    # De la base de datos y no de CoinGecko: el ciclo los acaba de guardar y
    # pedirlos otra vez gastaría el doble de consultas al mes.
    precios = {}
    for coin_id in (*vigiladas, *suyas):
        precio = database.get_last_price(config.database_path, coin_id)
        if precio is not None:
            precios[coin_id] = precio
    if not precios:
        return None

    lineas = [
        (c, precios[c], _variacion(config, c, precios[c]))
        for c in vigiladas
        if c in precios
    ]
    texto = alerts.formatear_resumen(lineas, config.vs_currency, envivo.TITULO)
    if config.cartera:
        texto += "\n\n" + _bloque_cartera(config, precios)
    return texto + "\n\n" + envivo.pie(ahora)


def _retirar_envivo(config: Config, numero: int) -> None:
    token, chat = config.telegram_token, config.telegram_chat_id
    # Borrado ya no queda fijado. Si es viejo no deja borrarlo: al menos lo suelto.
    if not telegram.borrar_mensaje(token, chat, numero):
        telegram.desfijar(token, chat, numero)


def _envivo(config: Config, argumento: str) -> Respuesta:
    try:
        poner = envivo.interpretar(argumento)
    except envivo.EnvivoError as e:
        return str(e)

    anterior = database.envivo(config.database_path)
    if not poner:
        if anterior is None:
            return "No lo tenías puesto. Para ponerlo: /envivo"
        _retirar_envivo(config, anterior)
        database.guardar_envivo(config.database_path, None)
        return "Hecho, quitado el mensaje en vivo. Para volver: /envivo"

    texto = _texto_envivo(config, datetime.now().astimezone())
    if texto is None:
        return "Todavía no tengo precios guardados. Prueba en unos minutos."
    token, chat = config.telegram_token, config.telegram_chat_id
    nuevo = telegram.enviar_con_id(token, chat, texto)
    if nuevo is None:
        return "No he podido mandarlo. Prueba en un rato."
    # Con uno ya puesto, /envivo lo baja al final del chat.
    if anterior is not None:
        _retirar_envivo(config, anterior)
    database.guardar_envivo(config.database_path, nuevo)

    minutos = max(1, round(config.check_interval / 60))
    cada = f"Lo actualizo solo cada {minutos} min, sin mandarte nada nuevo."
    if not telegram.fijar(token, chat, nuevo):
        return (
            f"📌 Ahí lo tienes. {cada}\n"
            "No he podido fijarlo: mantenlo pulsado y dale a Fijar."
        )
    return f"📌 Fijado arriba. {cada} Para quitarlo: /envivo no"


def en_vivo(config: Config, ahora: datetime | None = None) -> None:
    """Pone al día el mensaje de /envivo, si lo tienes."""
    try:
        numero = database.envivo(config.database_path)
        if numero is None:
            return
        texto = _texto_envivo(config, ahora or datetime.now().astimezone())
    except database.DatabaseError as e:
        logger.error("No se pudo preparar el mensaje en vivo: %s", e)
        return
    if texto is None:
        return

    error = telegram.editar_mensaje(
        config.telegram_token, config.telegram_chat_id, numero, texto
    )
    if error and envivo.se_perdio(error):
        logger.info("El mensaje en vivo ya no esta, dejo de actualizarlo")
        try:
            database.guardar_envivo(config.database_path, None)
        except database.DatabaseError as e:
            logger.error("No se pudo quitar el mensaje en vivo: %s", e)


def resumen_diario(config: Config, ahora: datetime | None = None) -> None:
    """Manda el resumen del dia si toca. Si falla, lo reintenta el siguiente ciclo."""
    config = _con_cambios(config)
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

    texto = montar_resumen(
        config,
        titulo=TITULO_DIARIO,
        pie=_linea_miedo(),
        con_cerca=True,
        aniversarios=ahora.date(),
    )
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


def copia_semanal(config: Config, hoy: date | None = None) -> None:
    """Manda la base de datos si toca. No es un aviso, así que /mute no la para."""
    if not config.copia_semanal:
        return

    hoy = hoy or date.today()
    ruta = config.database_path
    # Una copia que falla no puede contar como fallo del ciclo: acabaría parando el bot.
    try:
        if not backup.toca(database.ultimo_resumen(ruta, database.ULTIMA_COPIA), hoy):
            return

        contenido = backup.crear(ruta)
        if len(contenido) > backup.MAX_BYTES:
            telegram.send_message(
                config.telegram_token, config.telegram_chat_id, backup.GRANDE
            )
        elif not telegram.send_document(
            config.telegram_token,
            config.telegram_chat_id,
            contenido,
            backup.nombre(hoy),
            backup.pie(hoy),
            sin_sonido=True,
        ):
            logger.error("No se pudo enviar la copia, la reintento luego")
            return

        database.guardar_resumen(ruta, hoy, database.ULTIMA_COPIA)
    except (database.DatabaseError, OSError) as e:
        logger.error("No se pudo hacer la copia: %s", e)


def _linea_miedo() -> str | None:
    # Es un extra: si alternative.me no contesta, el resumen sale igual.
    try:
        return alerts.linea_miedo(miedo.pedir())
    except miedo.MiedoError as e:
        logger.warning("Sin indice de miedo en el resumen: %s", e)
        return None


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
    try:
        semana = _leer_semana(config)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer los precios de la semana: %s", e)
        return
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


def _leer_año(config: Config, año: int) -> anual.Año:
    desde, hasta = anual.tramo(año)
    posiciones = list(config.cartera)
    filas = []
    if posiciones:
        horas = (datetime.now(timezone.utc) - desde).total_seconds() / 3600
        filas = database.get_series(
            config.database_path,
            [p.coin_id for p in posiciones],
            horas,
            config.vs_currency,
        )
    filas = [f for f in filas if desde <= f[0] < hasta]
    todos = database.get_movimientos(config.database_path, None)
    return anual.calcular(año, posiciones, filas, todos)


def resumen_anual(config: Config, ahora: datetime | None = None) -> None:
    """El 1 de enero, a la hora del diario, cómo te fue el año que acaba de cerrar."""
    config = _con_cambios(config)
    if config.resumen_diario is None:
        return

    ahora = ahora or datetime.now().astimezone()
    try:
        ultimo = database.ultimo_resumen(config.database_path, database.ULTIMO_ANUAL)
    except database.DatabaseError as e:
        logger.error("No se pudo leer el ultimo resumen anual: %s", e)
        return

    if not anual.toca(ahora, config.resumen_diario, ultimo) or _silenciado(config):
        return

    año = ahora.astimezone().year - 1
    try:
        resultado = _leer_año(config, año)
    except database.DatabaseError as e:
        logger.error("No se pudo leer el año %d: %s", año, e)
        return

    if resultado.cartera is None and not resultado.compras and not resultado.ventas:
        logger.info("Toca el resumen de %d, pero no hay nada de ese año", año)
    elif not telegram.send_message(
        config.telegram_token,
        config.telegram_chat_id,
        alerts.formatear_anual(resultado, config.vs_currency, ahora.date()),
        botones=(
            botones.tarjeta_anual(año)
            if tarjeta_anual.calcular(resultado, ahora.date())
            else None
        ),
    ):
        logger.error("No se pudo enviar el resumen anual, lo reintento luego")
        return
    else:
        logger.info("Resumen de %d enviado", año)

    try:
        database.guardar_resumen(
            config.database_path, ahora.date(), database.ULTIMO_ANUAL
        )
    except database.DatabaseError as e:
        logger.error("No se pudo apuntar el resumen anual: %s", e)


def aviso_compensar(config: Config, ahora: datetime | None = None) -> None:
    """En diciembre, si vendiendo algo en pérdidas pagarías menos este año."""
    config = _con_cambios(config)
    if config.resumen_diario is None:
        return

    ahora = ahora or datetime.now().astimezone()
    try:
        ultimo = database.ultimo_resumen(config.database_path, database.AVISO_COMPENSAR)
    except database.DatabaseError as e:
        logger.error("No se pudo leer el aviso de compensar: %s", e)
        return
    if not compensar.toca_aviso(ahora, config.resumen_diario, ultimo):
        return
    if _silenciado(config):
        return

    hoy = ahora.astimezone().date()
    plan = _plan_compensar(config, hoy)
    # Sin precios lo intenta mañana; sin nada que ahorrar, también, por si vendes.
    if isinstance(plan, str) or not plan.ventas:
        return
    texto = (
        "⏰ <b>Aún llegas a pagar menos a Hacienda este año</b>\n\n"
        + alerts.formatear_compensar(plan, config.vs_currency, hoy)
    )
    if not telegram.send_message(config.telegram_token, config.telegram_chat_id, texto):
        logger.error("No se pudo enviar el aviso de compensar, lo reintento luego")
        return
    logger.info("Aviso de compensar enviado: te ahorrarías %.2f", plan.ahorro)
    try:
        database.guardar_resumen(config.database_path, hoy, database.AVISO_COMPENSAR)
    except database.DatabaseError as e:
        logger.error("No se pudo apuntar el aviso de compensar: %s", e)


def aviso_de_la_renta(config: Config, ahora: datetime | None = None) -> None:
    """En abril, si el año pasado vendiste o cobraste staking, que toca declararlo."""
    config = _con_cambios(config)
    if config.resumen_diario is None:
        return

    ahora = ahora or datetime.now().astimezone()
    try:
        ultimo = database.ultimo_resumen(config.database_path, database.AVISO_RENTA)
    except database.DatabaseError as e:
        logger.error("No se pudo leer el aviso de la Renta: %s", e)
        return
    if not aviso_renta.toca_aviso(ahora, config.resumen_diario, ultimo):
        return
    if _silenciado(config):
        return

    hoy = ahora.astimezone().date()
    año = hoy.year - 1
    todos = database.get_movimientos(config.database_path, None)
    i = impuestos.calcular(todos, año)
    recibido = impuestos.recompensas_de(todos, año)
    if aviso_renta.hay_que_declarar(i, recibido):
        if not telegram.send_message(
            config.telegram_token,
            config.telegram_chat_id,
            alerts.formatear_aviso_renta(i, config.vs_currency, recibido),
            botones=botones.para_renta(año) if i.ventas else None,
        ):
            logger.error("No se pudo enviar el aviso de la Renta, lo reintento luego")
            return
        logger.info("Aviso de la Renta de %d enviado", año)
    else:
        logger.info("Toca el aviso de la Renta, pero en %d no hay nada", año)
    # Apuntado también sin nada que declarar: si no, lo miraría cada ciclo hasta el 15.
    try:
        database.guardar_resumen(config.database_path, hoy, database.AVISO_RENTA)
    except database.DatabaseError as e:
        logger.error("No se pudo apuntar el aviso de la Renta: %s", e)


def resumen_mensual(config: Config, ahora: datetime | None = None) -> None:
    """El día 1, a la hora del diario, cómo le fue a la cartera el mes pasado."""
    config = _con_cambios(config)
    if config.resumen_diario is None or not config.cartera:
        return

    ahora = ahora or datetime.now().astimezone()
    try:
        ultimo = database.ultimo_resumen(config.database_path, database.ULTIMO_MENSUAL)
    except database.DatabaseError as e:
        logger.error("No se pudo leer el ultimo resumen mensual: %s", e)
        return

    if not mensual.toca(ahora, config.resumen_diario, ultimo) or _silenciado(config):
        return

    desde, hasta = mensual.tramo(ahora)
    horas = (datetime.now(timezone.utc) - desde).total_seconds() / 3600
    posiciones = list(config.cartera)
    try:
        filas = database.get_series(
            config.database_path,
            [p.coin_id for p in posiciones],
            horas,
            config.vs_currency,
        )
    except database.DatabaseError as e:
        logger.error("No se pudieron leer los precios del mes: %s", e)
        return
    # Lo de esta mañana ya es del mes nuevo.
    resultado = semanal.semana(posiciones, [f for f in filas if f[0] < hasta])

    nombre = mes.nombre(desde)
    if resultado is None:
        logger.info("Toca el resumen mensual, pero no hay precios de %s", nombre)
    else:
        respuesta = _foto_semana(
            config,
            resultado,
            horas,
            titulo=f"Tu {nombre}",
            tramo=f"en {nombre}",
            emoji="🗓",
            subtitulo=f"Del 1 al {(hasta - timedelta(days=1)).day} de {nombre}",
            pista=mes.pista(config.history_days, horas),
        )
        if not _mandar_foto(config, respuesta):
            logger.error("No se pudo enviar el resumen mensual, lo reintento luego")
            return
        logger.info("Resumen mensual enviado")

    try:
        database.guardar_resumen(
            config.database_path, ahora.date(), database.ULTIMO_MENSUAL
        )
    except database.DatabaseError as e:
        logger.error("No se pudo apuntar el resumen mensual: %s", e)


def _leer_semana(config: Config, horas: float = semanal.HORAS) -> semanal.Semana | None:
    posiciones = list(config.cartera)
    filas = database.get_series(
        config.database_path,
        [p.coin_id for p in posiciones],
        horas,
        config.vs_currency,
    )
    return semanal.semana(posiciones, filas)


def _foto_semana(
    config: Config,
    semana: semanal.Semana,
    horas: float = semanal.HORAS,
    titulo: str = "Tu semana",
    tramo: str = "en la semana",
    emoji: str = "📅",
    subtitulo: str | None = None,
    pista: str | None = None,
) -> str | comandos.Foto:
    primero = semana.serie[0][0]
    # Contra la hora de verdad, que es con la que se leyeron los precios.
    ahora = datetime.now(timezone.utc)
    desde = primero if periodo.falta_principio(primero, ahora, horas) else None
    if desde and subtitulo:
        subtitulo = f"Desde el {desde.astimezone():%d/%m}"
    texto = alerts.con_fuente(
        alerts.formatear_semana(
            semana,
            config.vs_currency,
            desde,
            f"{emoji} <b>{titulo}</b>",
            tramo,
            pista,
        )
    )

    invertidos = [p.invertido for p in config.cartera]
    invertido = None if None in invertidos else sum(invertidos)
    try:
        png = grafica.dibujar(
            "cartera",
            semana.serie,
            config.vs_currency,
            horas,
            titulo=titulo,
            invertido=invertido,
            subtitulo=subtitulo,
        )
    except Exception as e:
        logger.warning("Resumen semanal sin imagen: %s", e)
        return texto
    return comandos.Foto(png, texto, texto)


def _mandar_semana(config: Config, semana: semanal.Semana) -> bool:
    return _mandar_foto(config, _foto_semana(config, semana))


def _mandar_foto(config: Config, respuesta: str | comandos.Foto) -> bool:
    sin_sonido = _sin_sonido(config)
    if isinstance(respuesta, comandos.Foto):
        if telegram.send_photo(
            config.telegram_token,
            config.telegram_chat_id,
            respuesta.png,
            respuesta.pie,
            sin_sonido=sin_sonido,
        ):
            return True
        respuesta = respuesta.texto

    return telegram.send_message(
        config.telegram_token,
        config.telegram_chat_id,
        respuesta,
        sin_sonido=sin_sonido,
    )


def _semana(config: Config) -> str | comandos.Foto:
    config = _con_cambios(config)
    if not config.cartera:
        return SIN_CARTERA
    semana = _leer_semana(config)
    if semana is None:
        return "Aún no tengo precios de esta semana. Vuelve a preguntar en un rato."
    return _foto_semana(config, semana)


def _resumenia(config: Config) -> Respuesta:
    config = _con_cambios(config)
    if not config.cartera:
        return SIN_CARTERA
    semana = _leer_semana(config)
    if semana is None:
        return "Aún no tengo precios de esta semana. Vuelve a preguntar en un rato."
    valores = {}
    for p in config.cartera:
        precio = database.get_last_price(config.database_path, p.coin_id)
        if precio is not None:
            valores[p.coin_id] = p.cantidad * precio
    total = sum(valores.values())
    pesos = {c: v / total * 100 for c, v in valores.items()} if total else {}
    try:
        frases = resumenia.escribir(resumenia.datos(semana, config.vs_currency, pesos))
    except resumenia.ResumenIAError as e:
        return telegram.escape(str(e))
    return alerts.formatear_resumenia(frases)


def _panel(config: Config) -> Respuesta:
    url = panel.url_app()
    if not url.startswith("https://"):
        return alerts.PANEL_SIN_URL
    return comandos.ConBotones(alerts.PANEL_ABRIR, [[("Abrir el panel", url + "/app")]])


def _enlace(config: Config) -> Respuesta:
    url = panel.url_app()
    if not url.startswith("https://"):
        return alerts.PANEL_SIN_URL
    ahora = time.time()
    return alerts.formatear_enlace(
        panel.enlace(url, config.telegram_token, ahora),
        datetime.fromtimestamp(ahora + panel.VIDA_ENLACE, timezone.utc),
    )


def _mes(config: Config) -> str | comandos.Foto:
    ahora = datetime.now(timezone.utc)
    nombre = mes.nombre(ahora)
    return _desde_el_principio(
        config, mes.horas(ahora), f"Tu {nombre}", "mes", f"Desde el 1 de {nombre}"
    )


def _anual(config: Config, argumento: str = "") -> Respuesta:
    ahora = datetime.now(timezone.utc)
    quiere_tarjeta, argumento = tarjeta_anual.pedida(argumento)
    if quiere_tarjeta:
        return _tarjeta_anual(config, argumento)
    if argumento:
        try:
            año = anual.interpretar(argumento, date.today().year)
        except anual.AnualError as e:
            return telegram.escape(str(e))
        config = _con_cambios(config)
        a = _leer_año(config, año)
        texto = alerts.formatear_anual(a, config.vs_currency, date.today())
        if tarjeta_anual.calcular(a, date.today()) is None:
            return texto
        return comandos.ConBotones(texto, botones.tarjeta_anual(año))
    return _desde_el_principio(
        config,
        mes.horas_del_ano(ahora),
        f"Tu {ahora.astimezone().year}",
        "año",
        "Desde el 1 de enero",
    )


def _tarjeta_anual(config: Config, argumento: str) -> str | comandos.Foto:
    hoy = date.today()
    try:
        año = anual.interpretar(argumento, hoy.year) if argumento else hoy.year
    except anual.AnualError as e:
        return telegram.escape(str(e))
    config = _con_cambios(config)
    a = _leer_año(config, año)
    t = tarjeta_anual.calcular(a, hoy)
    if t is None:
        return (
            f"De {año} no tengo con qué hacerla: ni precios guardados de tu cartera "
            f"ni compras con las que comparar. Lo que haya, en /anual {año}"
        )
    texto = alerts.formatear_anual(a, config.vs_currency, hoy)
    try:
        png = grafica.dibujar_tarjeta_anual(t)
    except Exception as e:
        logger.warning("Mando la tarjeta de %d sin imagen: %s", año, e)
        return texto
    pie = f"🎆 Tu {año} en cripto, para enseñar: solo porcentajes, sin cifras."
    return comandos.Foto(png, pie, texto)


def _desde_el_principio(
    config: Config, horas: float, titulo: str, que: str, subtitulo: str
) -> str | comandos.Foto:
    config = _con_cambios(config)
    if not config.cartera:
        return SIN_CARTERA
    resultado = _leer_semana(config, horas)
    if resultado is None:
        return f"Aún no tengo precios de este {que}. Vuelve a preguntar en un rato."
    return _foto_semana(
        config,
        resultado,
        horas,
        titulo,
        f"en lo que va de {que}",
        "🗓️",
        # Si no, pondría "últimas 113,361 h".
        subtitulo,
        mes.pista(config.history_days, horas),
    )


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


def montar_resumen(
    config: Config,
    titulo: str | None = None,
    pie: str | None = None,
    con_cerca: bool = False,
    aniversarios: date | None = None,
) -> str | None:
    """El texto del resumen con los precios de ahora. None si no hay precios.

    con_cerca añade las /alerta que estan a punto de saltar. Con aniversarios,
    las compras que cumplen años ese día.
    """
    config = _con_cambios(config)
    coin_ids = [w.coin_id for w in config.watchlist]
    pendientes = _puntuales(config) if con_cerca else []
    cumplen = _cumplen(config, aniversarios) if aniversarios else []
    # Lo de la cartera y lo de las alertas puede no estar en la lista de
    # vigiladas, pero tambien necesita precio. Una sola consulta para todo.
    extra = [p.coin_id for p in (*config.cartera, *pendientes, *cumplen)]
    extra = [c for c in extra if c not in coin_ids and c != puntuales.CARTERA]

    precios = _consultar(config, coin_ids + list(dict.fromkeys(extra)))
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
    if pendientes:
        con_valor = dict(precios)
        valor = cartera.valor_total(list(config.cartera), precios)
        if valor is not None:
            con_valor[puntuales.CARTERA] = valor
        hay = puntuales.cerca(pendientes, con_valor)
        todas = puntuales.cerca(pendientes, con_valor, margen=math.inf)
        if hay:
            texto += "\n\n" + alerts.formatear_cerca(hay, config.vs_currency)
        elif todas:
            a, falta = todas[0]
            texto += "\n\n" + alerts.formatear_lejos(
                len(pendientes), a, falta, config.vs_currency
            )
    if cumplen:
        lista = aniversario.calcular(cumplen, precios, aniversarios)
        texto += "\n\n" + alerts.formatear_aniversarios(lista, config.vs_currency)
    if pie:
        texto += "\n\n" + pie

    return alerts.con_fuente(texto)


def _cumplen(config: Config, hoy: date) -> list[movimientos.Movimiento]:
    try:
        todos = database.get_movimientos(config.database_path, limite=None)
    except database.DatabaseError as e:
        # Es un extra: sin esto el resumen sale igual.
        logger.warning("Sin aniversarios en el resumen: %s", e)
        return []
    return aniversario.de_hoy(todos, hoy)


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
