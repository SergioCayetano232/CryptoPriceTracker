"""Punto de entrada: consulta precios, los guarda, compara y avisa.

Uso:
    python main.py                    una consulta y sale
    python main.py --loop             vigila en bucle
    python main.py --test             manda un mensaje de prueba a Telegram
    python main.py --status           manda un resumen de como van los precios
    python main.py --history bitcoin  muestra el historico guardado
"""

import argparse
import logging
import sys
import time

from crypto_tracker import alerts, coingecko, database, telegram
from crypto_tracker.config import Config, ConfigError, load_config

logger = logging.getLogger("crypto_tracker")

# Si el ciclo falla estas veces seguidas, algo va mal de verdad y paramos.
MAX_FALLOS = 10

# Con cuanto tiempo atras se compara el precio en el resumen.
HORAS_RESUMEN = 24


def configurar_logs(verbose: bool = False) -> None:
    """Deja los logs con hora y nivel, para saber que paso y cuando."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def ejecutar_ciclo(config: Config, estado: dict[str, str]) -> dict[str, str]:
    """Un ciclo completo: consultar, guardar, comparar y avisar.

    Devuelve el estado actualizado de las criptos. Si algo falla, lo
    registra y devuelve el estado sin tocar, para poder reintentar luego.
    """
    coin_ids = [w.coin_id for w in config.watchlist]

    try:
        precios = coingecko.get_prices(coin_ids, config.vs_currency)
    except coingecko.CoinGeckoError as e:
        logger.error("No se pudieron consultar los precios: %s", e)
        return estado

    if not precios:
        logger.warning("La consulta no devolvio ningun precio")
        return estado

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
        return estado_nuevo

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

    return estado_nuevo


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

    while True:
        try:
            estado = ejecutar_ciclo(config, estado)
            fallos = 0
        except KeyboardInterrupt:
            raise
        except Exception:
            # Red a la que caen los errores que no previmos. Sin esto, un
            # fallo raro a las 3 de la mañana mata el vigilante entero.
            fallos += 1
            logger.exception("Error inesperado en el ciclo (%d seguidos)", fallos)

            if fallos >= MAX_FALLOS:
                logger.error("Demasiados fallos seguidos, paro.")
                return 1

        try:
            time.sleep(config.check_interval)
        except KeyboardInterrupt:
            raise


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


def enviar_resumen(config: Config) -> int:
    """Consulta los precios de ahora y manda un resumen por Telegram."""
    coin_ids = [w.coin_id for w in config.watchlist]

    try:
        precios = coingecko.get_prices(coin_ids, config.vs_currency)
    except coingecko.CoinGeckoError as e:
        logger.error("No se pudieron consultar los precios: %s", e)
        return 1

    if not precios:
        logger.error("La consulta no devolvio ningun precio")
        return 1

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

    texto = alerts.formatear_resumen(lineas, config.vs_currency)

    if telegram.send_message(config.telegram_token, config.telegram_chat_id, texto):
        logger.info("Resumen enviado con %d criptos", len(lineas))
        return 0

    logger.error("No se pudo enviar el resumen")
    return 1


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

    # solo comparamos precios de la misma moneda, si no sale un % falso
    misma = [f for f in filas if f["currency"] == config.vs_currency]
    if len(misma) >= 2 and misma[-1]["price"]:
        variacion = (misma[0]["price"] - misma[-1]["price"]) / misma[-1]["price"] * 100
        print(f"\n  Variacion en el tramo mostrado: {variacion:+.2f}%")

    print()
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
