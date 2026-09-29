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
from datetime import datetime, timedelta, timezone

from crypto_tracker import (
    alerts,
    coingecko,
    comandos,
    database,
    diario,
    salud,
    telegram,
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

# Segundos que Telegram aguanta la conexion abierta esperando un mensaje.
ESPERA_TELEGRAM = 30

# Lo que escribiste con el bot apagado no se contesta: un /mute de anoche
# no pinta nada esta mañana.
ANTIGUEDAD_MAXIMA = 10 * 60


def configurar_logs(verbose: bool = False) -> None:
    """Deja los logs con hora y nivel, para saber que paso y cuando."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def ejecutar_ciclo(
    config: Config, estado: dict[str, str]
) -> tuple[dict[str, str], str | None]:
    """Un ciclo completo: consultar, guardar, comparar y avisar.

    Devuelve el estado actualizado y, si no hubo precios, el porque. Si algo
    falla, lo registra y devuelve el estado sin tocar para reintentar luego.
    """
    coin_ids = [w.coin_id for w in config.watchlist]

    try:
        precios = coingecko.get_prices(coin_ids, config.vs_currency)
    except coingecko.CoinGeckoError as e:
        logger.error("No se pudieron consultar los precios: %s", e)
        return estado, str(e)

    if not precios:
        logger.warning("La consulta no devolvio ningun precio")
        return estado, "La consulta no devolvio ningun precio"

    logger.info(
        "Precios: %s",
        ", ".join(f"{c}={p}" for c, p in sorted(precios.items())),
    )

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

    avisos, estado_nuevo = alerts.revisar(precios, config.watchlist, estado)

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
    callado = _silenciado(config)
    if callado:
        logger.info(
            "Silenciado hasta las %s, no aviso de: %s",
            callado.astimezone().strftime("%H:%M"),
            ", ".join(a.coin_id for a in avisos),
        )
        return estado_nuevo, None

    # Todo en un mensaje: si cruzan tres a la vez, tres notificaciones
    # seguidas molestan y encima Telegram empieza a cortar el ritmo.
    texto = alerts.formatear_varios(avisos, config.vs_currency)
    cruzadas = ", ".join(f"{a.coin_id} {a.estado}" for a in avisos)

    if telegram.send_message(config.telegram_token, config.telegram_chat_id, texto):
        logger.info("Aviso enviado (%d): %s", len(avisos), cruzadas)
    else:
        # El aviso se perdio, pero el estado ya cambio. No insistimos:
        # el siguiente cruce volvera a avisar.
        logger.error("No se pudo avisar de: %s", cruzadas)

    return estado_nuevo, None


def ejecutar_bucle(config: Config, estado: dict[str, str]) -> int:
    """Repite el ciclo cada CHECK_INTERVAL segundos hasta que se corte.

    Aguanta los fallos sueltos: si algo revienta de forma inesperada lo
    registra y sigue. Solo se rinde si falla muchas veces seguidas.
    """
    logger.info(
        "Modo bucle cada %ds. Ctrl+C para parar.",
        config.check_interval,
    )

    fallos = 0
    pulso = salud.Pulso()
    offset = None

    if not telegram.set_commands(config.telegram_token, comandos.COMANDOS):
        logger.warning("No se pudo poner el menu de comandos en Telegram")

    while True:
        try:
            estado, problema = ejecutar_ciclo(config, estado)
            fallos = 0
            resumen_diario(config)
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

        offset = esperar_escuchando(config, config.check_interval, offset)


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
    orden = comandos.interpretar(texto)

    try:
        respuesta = responder(config, *orden) if orden else comandos.NO_ENTIENDO
    except database.DatabaseError as e:
        logger.error("Error de la base de datos contestando '%s': %s", texto, e)
        respuesta = "⚠️ Algo ha fallado con la base de datos. Mira el log."

    telegram.send_message(config.telegram_token, config.telegram_chat_id, respuesta)


def responder(config: Config, nombre: str, argumento: str) -> str:
    """El texto con el que se contesta a cada comando."""
    if nombre == "ayuda":
        return comandos.AYUDA

    if nombre == "status":
        texto = montar_resumen(config)
        return texto or "No he podido consultar los precios. Prueba en un rato."

    if nombre == "mute":
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

    if nombre == "historico":
        return _historico(config, argumento.strip().lower())

    return comandos.NO_ENTIENDO


def _historico(config: Config, coin_id: str) -> str:
    if not coin_id:
        return "¿De cuál? Por ejemplo: /historico bitcoin"

    precios = database.get_prices_since(
        config.database_path, coin_id, HORAS_RESUMEN, config.vs_currency
    )
    vigiladas = {w.coin_id for w in config.watchlist}
    if len(precios) < 2 and coin_id in vigiladas:
        # Recien instalado: el id esta bien, lo que falta es tiempo.
        return (
            f"Aún tengo pocos precios de <b>{telegram.escape(coin_id)}</b>. "
            "Vuelve a preguntar dentro de un rato."
        )
    if len(precios) < 2:
        return (
            f"No tengo precios de <b>{telegram.escape(coin_id)}</b> de las "
            f"últimas {HORAS_RESUMEN} h. Tiene que ser el id de CoinGecko "
            "(bitcoin, no BTC)."
        )

    return alerts.formatear_historico(
        coin_id, precios, config.vs_currency, HORAS_RESUMEN
    )


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

    if not telegram.send_message(config.telegram_token, config.telegram_chat_id, texto):
        logger.error("No se pudo enviar el resumen diario, lo reintento luego")
        return

    logger.info("Resumen diario enviado")
    try:
        database.guardar_resumen(config.database_path, ahora.date())
    except database.DatabaseError as e:
        logger.error("No se pudo apuntar el resumen, puede que llegue repetido: %s", e)


def _avisar_salud(config: Config, texto: str) -> None:
    """Manda los avisos de caida y vuelta. No se callan con --mute."""
    if telegram.send_message(config.telegram_token, config.telegram_chat_id, texto):
        logger.info("Aviso de estado enviado")
    else:
        logger.error("No se pudo mandar el aviso de estado")


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
    coin_ids = [w.coin_id for w in config.watchlist]

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

    lineas = []
    for coin_id in coin_ids:
        precio = precios.get(coin_id)
        if precio is None:
            continue
        lineas.append((coin_id, precio, _variacion(config, coin_id, precio)))

    if titulo:
        return alerts.formatear_resumen(lineas, config.vs_currency, titulo)
    return alerts.formatear_resumen(lineas, config.vs_currency)


def _variacion(config: Config, coin_id: str, precio: float) -> float | None:
    """Cuanto ha variado en porcentaje desde hace HORAS_RESUMEN horas."""
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
    parser.add_argument(
        "--unmute", action="store_true", help="vuelve a avisar y sale"
    )
    parser.add_argument(
        "--history",
        metavar="CRIPTO",
        help="muestra el historico guardado de una cripto y sale",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="logs detallados")
    args = parser.parse_args()

    configurar_logs(args.verbose)

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
        return enviar_resumen(config)

    # Recuperamos en que zona quedo cada cripto la ultima vez, asi no
    # repetimos avisos ya mandados aunque el programa se haya reiniciado.
    try:
        estado = database.load_state(config.database_path)
    except database.DatabaseError as e:
        logger.warning("No se pudo leer el estado anterior: %s", e)
        estado = {}

    logger.info("Vigilando %d criptos en %s", len(config.watchlist), config.vs_currency)

    if args.loop:
        return ejecutar_bucle(config, estado)

    ejecutar_ciclo(config, estado)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # Ctrl+C es una salida normal, no un error: nada de traceback.
        logger.info("Parado por el usuario")
        sys.exit(0)
