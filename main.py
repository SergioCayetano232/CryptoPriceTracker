"""Punto de entrada: consulta precios, los guarda, compara y avisa.

Uso:
    python main.py           una consulta y sale
    python main.py --test    manda un mensaje de prueba a Telegram
"""

import argparse
import logging
import sys

from crypto_tracker import alerts, coingecko, database, telegram
from crypto_tracker.config import Config, ConfigError, load_config

logger = logging.getLogger("crypto_tracker")


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

    avisos, estado_nuevo = alerts.revisar(precios, config.watchlist, estado)

    if not avisos:
        logger.info("Ningun umbral cruzado")
        return estado_nuevo

    for aviso in avisos:
        texto = alerts.formatear(aviso, config.vs_currency)
        enviado = telegram.send_message(
            config.telegram_token, config.telegram_chat_id, texto
        )
        if enviado:
            logger.info("Aviso enviado: %s %s", aviso.coin_id, aviso.estado)
        else:
            # El aviso se perdio, pero el estado ya cambio. No insistimos:
            # el siguiente cruce volvera a avisar.
            logger.error("No se pudo avisar de %s", aviso.coin_id)

    return estado_nuevo


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Notificador de precios de cripto")
    parser.add_argument(
        "--test", action="store_true", help="manda un mensaje de prueba y sale"
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

    logger.info("Vigilando %d criptos en %s", len(config.watchlist), config.vs_currency)
    ejecutar_ciclo(config, {})
    return 0


if __name__ == "__main__":
    sys.exit(main())
