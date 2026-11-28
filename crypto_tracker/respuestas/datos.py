"""Tus datos: sacarlos en CSV, la copia de seguridad y rellenar los huecos."""

import logging
from datetime import date, datetime, timezone

from ..avisos import alerts
from ..informes import exportar
from ..nucleo import (
    backup,
    coingecko,
    comandos,
    database,
    periodo,
    rellenar,
    simbolos,
    telegram,
)
from ..nucleo.config import Config
from .base import _con_cambios

logger = logging.getLogger("crypto_tracker")


def _backup(config: Config) -> str | comandos.Archivo:
    try:
        contenido = backup.crear(config.database_path)
    except (database.DatabaseError, OSError) as e:
        logger.error("No se pudo hacer la copia: %s", e)
        return backup.FALLO
    if len(contenido) > backup.MAX_BYTES:
        return backup.GRANDE

    hoy = date.today()
    return comandos.Archivo(
        contenido, backup.nombre(hoy), backup.pie(hoy), backup.FALLO
    )


def _rellenar(config: Config, argumento: str) -> str:
    try:
        coin_ids, dias = rellenar.interpretar(argumento, config.history_days)
    except rellenar.RellenarError as e:
        return telegram.escape(str(e))

    if not coin_ids:
        vigiladas = _con_cambios(config).watchlist
        coin_ids = [w.coin_id for w in vigiladas][: simbolos.MAX_VARIAS]
    if not coin_ids:
        return f"¿De cuál? Por ejemplo: {rellenar.EJEMPLO}"
    if len(coin_ids) > simbolos.MAX_VARIAS:
        return f"Como mucho {simbolos.MAX_VARIAS} a la vez."

    hechos, fallos = [], []
    for coin_id in coin_ids:
        try:
            bajados = coingecko.historico(coin_id, dias, config.vs_currency)
        except coingecko.CoinGeckoError as e:
            fallos.append((coin_id, str(e)))
            continue
        if not bajados:
            fallos.append((coin_id, "CoinGecko no tiene precios suyos"))
            continue

        serie = database.get_serie(
            config.database_path, coin_id, dias * 24 + 1, config.vs_currency
        )
        nuevos = rellenar.faltan(bajados, [cuando for cuando, _ in serie])
        database.guardar_serie(
            config.database_path, coin_id, nuevos, config.vs_currency
        )
        desde = nuevos[0][0] if nuevos else None
        hechos.append(rellenar.Relleno(coin_id, len(nuevos), desde))

    return alerts.con_fuente(alerts.formatear_rellenar(hechos, fallos, dias))


def _exportar_movimientos(config: Config) -> str | comandos.Archivo:
    lista = database.get_movimientos(config.database_path, None)
    if not lista:
        return (
            "Todavía no has apuntado ninguna compra ni venta. "
            "Se hace con /compra y /venta"
        )

    cuantos = "1 movimiento" if len(lista) == 1 else f"{len(lista)} movimientos"
    return comandos.Archivo(
        exportar.movimientos_a_csv(lista, config.vs_currency),
        exportar.nombre_movimientos(date.today()),
        f"📄 {cuantos}, del más antiguo al más nuevo\n"
        "<i>Solo lo apuntado con /compra y /venta, no el PORTFOLIO del .env</i>",
        "No he podido mandarte el archivo. Prueba en un rato.",
    )


def _exportar(config: Config, argumento: str) -> str | comandos.Archivo:
    try:
        if exportar.pide_movimientos(argumento):
            return _exportar_movimientos(config)
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
