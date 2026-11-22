"""Los avisos que el ciclo mira por su cuenta, aparte de los de precio.

Cada revisar_* manda su aviso al momento o, dentro del ciclo, lo deja en el
buzón para que salgan todos juntos en un mensaje.
"""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime, timezone
from functools import partial

from .. import (
    alertaratio,
    alerts,
    avisorsi,
    bajon,
    buzon,
    calma,
    cartera,
    coingecko,
    comisionred,
    concentracion,
    cruce,
    database,
    direccion,
    equilibrio,
    estables,
    funding,
    ideal,
    juntas,
    modelo721,
    puntuales,
    record,
    rezagada,
    rsi,
    salvo,
    telegram,
    volatilidad,
    volumen,
)
from ..config import Config
from .base import (
    _alertas_ratio,
    _direcciones_guardadas,
    _medir_pareja,
    _silenciado,
    _sin_sonido,
    _variacion,
)

logger = logging.getLogger("crypto_tracker")


def _avisar(
    config: Config,
    texto: str,
    sueltos: buzon.Buzon | None,
    al_llegar: Callable[[], None],
) -> bool:
    """Lo manda ya o, dentro del ciclo, lo deja para el mensaje del final."""
    if sueltos is not None:
        sueltos.echar(texto, al_llegar)
        return True
    if not telegram.send_message(
        config.telegram_token,
        config.telegram_chat_id,
        texto,
        sin_sonido=_sin_sonido(config),
    ):
        return False
    al_llegar()
    return True


def revisar_bajon(
    config: Config,
    valor: float | None,
    calladas: set[str],
    sueltos: buzon.Buzon | None = None,
) -> None:
    """Avisa si la cartera ha caído CAIDA_CARTERA desde su récord."""
    if config.caida_cartera is None or valor is None:
        return
    # Callado no se apunta: si sigue igual de abajo, avisa al volver.
    if puntuales.CARTERA in calladas or _silenciado(config):
        return

    posiciones = list(config.cartera)
    try:
        filas = database.get_series(
            config.database_path,
            [p.coin_id for p in posiciones],
            record.horas(config.history_days),
            config.vs_currency,
        )
        avisado = database.ultimo_bajon(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudo mirar el récord de la cartera: %s", e)
        return

    # El de ahora al final por si no se pudo guardar.
    serie = cartera.serie_valor(posiciones, filas)
    serie.append((datetime.now(timezone.utc), valor))
    resultado = record.calcular(serie)
    if resultado is None:
        return
    escalon = bajon.toca(resultado, config.caida_cartera, avisado)
    if escalon is None:
        return

    texto = alerts.formatear_bajon(
        resultado, escalon, config.caida_cartera, config.vs_currency
    )

    def apuntar() -> None:
        logger.info("Aviso de caída de la cartera: %.2f%%", resultado.caida)
        try:
            database.guardar_bajon(config.database_path, resultado.cuando, escalon)
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar el aviso de caída de la cartera: %s", e)

    if not _avisar(config, texto, sueltos, apuntar):
        logger.error("No se pudo avisar de la caída de la cartera")


def revisar_concentracion(
    config: Config,
    precios: dict[str, float],
    calladas: set[str],
    sueltos: buzon.Buzon | None = None,
) -> None:
    """Avisa una vez si una cripto pasa de CONCENTRACION de la cartera."""
    if config.concentracion is None or not config.cartera:
        return
    if puntuales.CARTERA in calladas or _silenciado(config):
        return
    valores, faltan = cartera.valorar(list(config.cartera), precios)
    # Sin el precio de una, las demás pesarían más de lo que pesan.
    if faltan:
        return

    try:
        avisado = database.ultima_concentracion(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudo leer el aviso de concentración: %s", e)
        return

    def apuntar(nuevo: str | None) -> None:
        if nuevo == avisado:
            return
        try:
            database.guardar_concentracion(config.database_path, nuevo)
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar el aviso de concentración: %s", e)

    c = concentracion.mayor(valores)
    if not concentracion.toca(c, config.concentracion, avisado):
        apuntar(concentracion.sigue(c, config.concentracion, avisado))
        return

    def avisada() -> None:
        logger.info("Aviso de concentración: %s es el %.1f%%", c.coin_id, c.peso)
        apuntar(c.coin_id)

    if not _avisar(config, alerts.formatear_concentracion(c), sueltos, avisada):
        logger.error("No se pudo avisar de la concentración de la cartera")


def revisar_ideal(
    config: Config,
    precios: dict[str, float],
    calladas: set[str],
    sueltos: buzon.Buzon | None = None,
) -> None:
    """Avisa una vez si la cartera se aleja del reparto de /ideal."""
    if not config.cartera:
        return
    try:
        suyo = ideal.de_texto(database.reparto_ideal(config.database_path))
        avisado = suyo is not None and database.ideal_avisado(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudo leer el reparto ideal: %s", e)
        return
    if suyo is None:
        return
    if puntuales.CARTERA in calladas or _silenciado(config):
        return
    valores, faltan = cartera.valorar(list(config.cartera), precios)
    # Sin el precio de una, las demás pesarían más de lo que pesan.
    if faltan:
        return

    def apuntar(nuevo: bool) -> None:
        if nuevo == avisado:
            return
        try:
            database.marcar_ideal_avisado(config.database_path, nuevo)
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar el aviso del reparto ideal: %s", e)

    lista = ideal.partes(valores, suyo.reparto)
    if not ideal.toca(lista, suyo.margen, avisado):
        apuntar(ideal.sigue_avisado(lista, suyo.margen, avisado))
        return

    def avisada() -> None:
        logger.info(
            "Aviso de reparto: %s a %.1f puntos", lista[0].coin_id, lista[0].puntos
        )
        apuntar(True)

    if not _avisar(config, alerts.formatear_aviso_ideal(lista, suyo), sueltos, avisada):
        logger.error("No se pudo avisar de que la cartera se aleja del reparto")


def revisar_equilibrio(
    config: Config,
    precios: dict[str, float],
    calladas: set[str],
    sueltos: buzon.Buzon | None = None,
) -> None:
    """Avisa una vez cuando una que estaba en pérdidas vuelve a lo que costó."""
    if not config.cartera or _silenciado(config):
        return
    valores, _ = cartera.valorar(list(config.cartera), precios)
    criptos = equilibrio.calcular(valores).criptos
    if not criptos:
        return
    try:
        esperando = database.esperando_equilibrio(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudo mirar quién estaba en pérdidas: %s", e)
        return

    def apuntar(e: equilibrio.Equilibrio, antes: bool, sigue: bool) -> None:
        if sigue == antes:
            return
        try:
            database.guardar_equilibrio(config.database_path, e.coin_id, sigue)
        except database.DatabaseError as err:
            logger.error("No se pudo apuntar el coste de %s: %s", e.coin_id, err)

    def avisada(e: equilibrio.Equilibrio, antes: bool, sigue: bool) -> None:
        logger.info("%s vuelve a su precio medio, %s", e.coin_id, e.medio)
        apuntar(e, antes, sigue)

    for e in criptos:
        if e.coin_id in calladas:
            continue
        antes = e.coin_id in esperando
        avisar, sigue = equilibrio.vuelta(e, antes)
        if not avisar:
            apuntar(e, antes, sigue)
        elif not _avisar(
            config,
            alerts.formatear_vuelta(e, config.vs_currency),
            sueltos,
            partial(avisada, e, antes, sigue),
        ):
            # Sin apuntarlo, lo vuelve a intentar el siguiente ciclo.
            logger.error("No se pudo avisar de que %s vuelve a su coste", e.coin_id)


def revisar_estables(
    config: Config,
    coin_ids: list[str],
    calladas: set[str],
    sueltos: buzon.Buzon | None = None,
) -> None:
    """Avisa una vez si una estable que tienes o vigilas se sale de su dólar."""
    if _silenciado(config):
        return
    precios_usd = {}
    for coin_id in estables.de_las_tuyas(coin_ids):
        precio = coingecko.precio_usd(coin_id)
        if precio is not None and coin_id not in calladas:
            precios_usd[coin_id] = precio
    if not precios_usd:
        return

    try:
        avisadas = database.estables_avisadas(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudo leer el aviso de las estables: %s", e)
        return

    def apuntar(d: estables.Desvio, fuera: bool) -> None:
        logger.info("%s a $%.4f", d.simbolo, d.precio)
        try:
            database.guardar_estable(config.database_path, d.coin_id, fuera)
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar el aviso de %s: %s", d.simbolo, e)

    salen, vuelven = estables.revisar(precios_usd, avisadas)
    for d in salen + vuelven:
        fuera = d in salen
        # Si no llega, no se apunta y lo intenta el siguiente ciclo.
        if not _avisar(
            config,
            alerts.formatear_estable(d, vuelve=not fuera),
            sueltos,
            partial(apuntar, d, fuera),
        ):
            logger.error("No se pudo avisar de %s", d.simbolo)


def revisar_721(
    config: Config,
    valor: float | None,
    calladas: set[str],
    sueltos: buzon.Buzon | None = None,
) -> None:
    """Avisa una vez al año cuando la cartera pasa del límite del modelo 721."""
    if not config.aviso_721 or valor is None:
        return
    if puntuales.CARTERA in calladas or _silenciado(config):
        return

    hoy = date.today()
    try:
        avisado = database.ultimo_resumen(config.database_path, database.AVISO_721)
    except database.DatabaseError as e:
        logger.error("No se pudo leer el aviso del modelo 721: %s", e)
        return
    if not modelo721.toca_avisar(valor, avisado, hoy):
        return

    def apuntar() -> None:
        logger.info("Aviso del modelo 721: la cartera vale %.2f", valor)
        try:
            database.guardar_resumen(config.database_path, hoy, database.AVISO_721)
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar el aviso del modelo 721: %s", e)

    if not _avisar(config, alerts.formatear_aviso_721(valor, hoy), sueltos, apuntar):
        logger.error("No se pudo avisar del modelo 721")


def revisar_calma(
    config: Config,
    vigiladas: dict[str, float],
    calladas: set[str],
    sueltos: buzon.Buzon | None = None,
) -> None:
    """Avisa una vez cuando una que vigilas lleva una semana mucho más quieta."""
    if not config.aviso_calma or _silenciado(config):
        return

    def apuntar(coin_id: str, avisada: bool, nueva: bool) -> None:
        if nueva == avisada:
            return
        try:
            database.guardar_calma_avisada(config.database_path, coin_id, nueva)
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar la calma de %s: %s", coin_id, e)

    def avisada_ya(coin_id: str, r: calma.Calma, avisada: bool, nueva: bool) -> None:
        logger.info("Calma en %s: %.1f%% en una semana", coin_id, r.rango)
        apuntar(coin_id, avisada, nueva)

    for coin_id in vigiladas:
        if coin_id in calladas:
            continue
        try:
            resultado = _calma_de(config, coin_id)
            avisada = database.calma_avisada(config.database_path, coin_id)
        except database.DatabaseError as e:
            logger.error("No se pudo mirar la calma de %s: %s", coin_id, e)
            continue
        if resultado is None:
            continue

        nueva = calma.sigue(resultado, avisada)
        if not calma.toca(resultado, avisada):
            apuntar(coin_id, avisada, nueva)
        elif not _avisar(
            config,
            alerts.formatear_aviso_calma(coin_id, resultado, config.vs_currency),
            sueltos,
            partial(avisada_ya, coin_id, resultado, avisada, nueva),
        ):
            # Sin apuntarlo, lo vuelve a intentar el siguiente ciclo.
            logger.error("No se pudo avisar de la calma de %s", coin_id)


def _calma_de(config: Config, coin_id: str) -> calma.Calma | None:
    serie = database.get_serie(
        config.database_path, coin_id, calma.HORAS, config.vs_currency
    )
    return calma.calcular(volatilidad.por_dias(serie))


def revisar_volumen(
    config: Config,
    vigiladas: dict[str, float],
    calladas: set[str],
    sueltos: buzon.Buzon | None = None,
) -> None:
    """Avisa una vez cuando una que vigilas mueve el triple de lo normal."""
    if not config.aviso_volumen or _silenciado(config):
        return

    def apuntar(coin_id: str, avisado: bool, nuevo: bool) -> None:
        if nuevo == avisado:
            return
        try:
            database.guardar_volumen_avisado(config.database_path, coin_id, nuevo)
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar el volumen de %s: %s", coin_id, e)

    def avisado_ya(v: volumen.Volumen, avisado: bool, nuevo: bool) -> None:
        logger.info("Volumen raro en %s: %.1f veces", v.coin_id, v.veces)
        apuntar(v.coin_id, avisado, nuevo)

    ahora = datetime.now(timezone.utc)
    for coin_id, actual in coingecko.volumenes(list(vigiladas)).items():
        if coin_id in calladas:
            continue
        try:
            serie = database.get_volumenes(
                config.database_path, coin_id, volumen.HORAS, config.vs_currency
            )
            avisado = database.volumen_avisado(config.database_path, coin_id)
        except database.DatabaseError as e:
            logger.error("No se pudo mirar el volumen de %s: %s", coin_id, e)
            continue

        normal = volumen.normal(serie, ahora)
        if normal is None:
            continue
        v = volumen.Volumen(
            coin_id, actual, normal, vigiladas[coin_id], coingecko.cambio_24h(coin_id)
        )

        nuevo = volumen.sigue(v, avisado)
        if not volumen.toca(v, avisado):
            apuntar(coin_id, avisado, nuevo)
        elif not _avisar(
            config,
            alerts.formatear_volumen(v, config.vs_currency),
            sueltos,
            partial(avisado_ya, v, avisado, nuevo),
        ):
            # Sin apuntarlo, lo vuelve a intentar el siguiente ciclo.
            logger.error("No se pudo avisar del volumen de %s", coin_id)


def revisar_cruces(
    config: Config,
    vigiladas: dict[str, float],
    calladas: set[str],
    sueltos: buzon.Buzon | None = None,
) -> None:
    """Avisa cuando la media de 50 días de una que vigilas cruza la de 200."""
    if not config.aviso_cruce or _silenciado(config):
        return

    def apuntar(coin_id: str, avisado: str | None, nuevo: str | None) -> None:
        if nuevo is None or nuevo == avisado:
            return
        try:
            database.guardar_lado_cruce(config.database_path, coin_id, nuevo)
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar el cruce de %s: %s", coin_id, e)

    def avisado_ya(c: cruce.Cruce, avisado: str | None, nuevo: str | None) -> None:
        logger.info("Cruce de medias: %s %s", c.coin_id, c.lado)
        apuntar(c.coin_id, avisado, nuevo)

    ahora = datetime.now(timezone.utc)
    for coin_id, precio in vigiladas.items():
        if coin_id in calladas:
            continue
        try:
            serie = database.get_serie(
                config.database_path, coin_id, cruce.HORAS, config.vs_currency
            )
            avisado = database.lado_cruce(config.database_path, coin_id)
        except database.DatabaseError as e:
            logger.error("No se pudo mirar el cruce de %s: %s", coin_id, e)
            continue

        # El de ahora al final por si no se pudo guardar.
        dias = volatilidad.por_dias([*serie, (ahora, precio)])
        c = cruce.calcular(coin_id, dias, precio)
        if c is None:
            continue

        nuevo = cruce.apuntar(c, avisado)
        if not cruce.toca(c, avisado):
            apuntar(coin_id, avisado, nuevo)
        elif not _avisar(
            config,
            alerts.formatear_cruce(c, config.vs_currency),
            sueltos,
            partial(avisado_ya, c, avisado, nuevo),
        ):
            # Sin apuntarlo, lo vuelve a intentar el siguiente ciclo.
            logger.error("No se pudo avisar del cruce de %s", coin_id)


def revisar_direcciones(
    config: Config, precios: dict[str, float], sueltos: buzon.Buzon | None = None
) -> None:
    """Avisa cuando entra o sale algo de una de /direccion."""
    if _silenciado(config):
        return
    try:
        vigiladas = _direcciones_guardadas(config)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer las direcciones: %s", e)
        return

    def apuntar(v: direccion.Vigilada, saldo: direccion.Saldo, cambio: int) -> None:
        logger.info("Se ha movido la dirección %s: %+d sats", v.nombre, cambio)
        nueva = direccion.Vigilada(v.direccion, v.nombre, saldo.sats, saldo.txs)
        try:
            database.guardar_direccion(
                config.database_path, v.direccion, nueva.guardar()
            )
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar la dirección %s: %s", v.nombre, e)

    for v in vigiladas:
        try:
            saldo = direccion.pedir(v.direccion)
        except direccion.DireccionError as e:
            logger.warning("No se pudo mirar %s: %s", v.direccion, e)
            continue
        cambio = direccion.movida(v, saldo)
        if cambio is None:
            continue

        if not _avisar(
            config,
            alerts.formatear_movimiento_direccion(
                v, cambio, saldo, precios, config.vs_currency
            ),
            sueltos,
            partial(apuntar, v, saldo, cambio),
        ):
            # Sin apuntarlo, lo vuelve a intentar el siguiente ciclo.
            logger.error("No se pudo avisar de que se movió %s", v.nombre)


def revisar_comisionred(config: Config, sueltos: buzon.Buzon | None = None) -> None:
    """Avisa una vez cuando mover bitcoin baja a lo que pediste en /comisionred."""
    try:
        limite = database.aviso_comisionred(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudo leer el aviso de la comisión de red: %s", e)
        return
    # Callado se queda puesto: si sigue barato al volver, salta entonces.
    if limite is None or _silenciado(config):
        return
    try:
        datos = comisionred.leer(comisionred.pedir_ahora(), [])
    except comisionred.ComisionRedError as e:
        logger.warning("No se pudo mirar la comisión de red: %s", e)
        return
    if not comisionred.toca(datos, limite):
        return

    def avisada() -> None:
        logger.info("Aviso de comisión de red: ha bajado a %d sat/vB", limite)
        try:
            database.guardar_aviso_comisionred(config.database_path, None)
        except database.DatabaseError as e:
            logger.error("No se pudo quitar el aviso de la comisión de red: %s", e)

    try:
        precio = database.get_last_price(config.database_path, "bitcoin")
    except database.DatabaseError:
        precio = None
    texto = alerts.formatear_aviso_comisionred(
        datos, limite, precio, config.vs_currency
    )
    if not _avisar(config, texto, sueltos, avisada):
        logger.error("No se pudo avisar de la comisión de red")


def revisar_rsi(
    config: Config,
    vigiladas: dict[str, float],
    calladas: set[str],
    sueltos: buzon.Buzon | None = None,
) -> None:
    """Avisa una vez cuando una que vigilas entra en sobrecompra o sobreventa."""
    if not config.aviso_rsi or _silenciado(config):
        return

    def apuntar(coin_id: str, avisado: str | None, nueva: str | None) -> None:
        if nueva == avisado:
            return
        try:
            database.guardar_zona_rsi(config.database_path, coin_id, nueva)
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar el aviso de RSI de %s: %s", coin_id, e)

    def avisado_ya(coin_id: str, r: rsi.Rsi, avisado: str | None, zona: str) -> None:
        logger.info("Aviso de RSI: %s en %.0f", coin_id, r.valor)
        apuntar(coin_id, avisado, zona)

    ahora = datetime.now(timezone.utc)
    for coin_id, precio in vigiladas.items():
        if coin_id in calladas:
            continue
        try:
            serie = database.get_serie(
                config.database_path, coin_id, rsi.HORAS, config.vs_currency
            )
            avisado = database.zona_rsi(config.database_path, coin_id)
        except database.DatabaseError as e:
            logger.error("No se pudo mirar el RSI de %s: %s", coin_id, e)
            continue

        # El de ahora al final por si no se pudo guardar.
        resultado = rsi.calcular(volatilidad.por_dias([*serie, (ahora, precio)]))
        if resultado is None:
            continue

        zona = avisorsi.toca(resultado.valor, avisado)
        if zona is None:
            apuntar(coin_id, avisado, avisorsi.sigue(resultado.valor, avisado))
        elif not _avisar(
            config,
            alerts.formatear_aviso_rsi(coin_id, resultado, config.vs_currency),
            sueltos,
            partial(avisado_ya, coin_id, resultado, avisado, zona),
        ):
            logger.error("No se pudo avisar del RSI de %s", coin_id)


def revisar_alertas_ratio(
    config: Config,
    precios: dict[str, float],
    calladas: set[str],
    sueltos: buzon.Buzon | None = None,
) -> None:
    """Las de /alerta eth/btc: saltan una vez y se borran."""
    if _silenciado(config):
        return
    for a in _alertas_ratio(config):
        if a.coin_id in calladas or a.contra in calladas:
            continue
        una, otra = precios.get(a.coin_id), precios.get(a.contra)
        if not (una and otra) or not alertaratio.cumplida(a, una / otra):
            continue
        if not _avisar(
            config,
            alerts.formatear_aviso_ratio(a, una / otra),
            sueltos,
            partial(
                database.quitar_alerta_ratio, config.database_path, a.coin_id, a.contra
            ),
        ):
            logger.error("No se pudo avisar del ratio %s/%s", a.coin_id, a.contra)


def revisar_rezagadas(
    config: Config, precios: dict[str, float], sueltos: buzon.Buzon | None = None
) -> None:
    """Las de /rezagada: una semana de una contra la de la otra."""
    if _silenciado(config):
        return

    def apuntar(r: rezagada.Rezagada, avisada: bool) -> None:
        if avisada != r.avisada:
            database.guardar_rezagada(config.database_path, replace(r, avisada=avisada))

    try:
        lista = database.get_rezagadas(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer las de /rezagada: %s", e)
        return
    for r in lista:
        ahora, contra = precios.get(r.coin_id), precios.get(r.contra)
        try:
            antes = database.get_price_at(
                config.database_path, r.coin_id, rezagada.HORAS
            )
            contra_antes = database.get_price_at(
                config.database_path, r.contra, rezagada.HORAS
            )
        except database.DatabaseError as e:
            logger.error("Sin histórico para /rezagada: %s", e)
            return
        # Sin una semana guardada no hay con qué comparar todavía.
        if not (ahora and contra and antes and contra_antes):
            continue

        dif = rezagada.diferencia(ahora, antes, contra, contra_antes)
        avisar, avisada = rezagada.toca(r, dif)
        if not avisar:
            apuntar(r, avisada)
        elif not _avisar(
            config,
            alerts.formatear_aviso_rezagada(
                r, dif, (ahora / antes - 1) * 100, (contra / contra_antes - 1) * 100
            ),
            sueltos,
            partial(apuntar, r, avisada),
        ):
            logger.error("No se pudo avisar de que %s se queda atrás", r.coin_id)


def revisar_funding(
    config: Config,
    calladas: set[str],
    sueltos: buzon.Buzon | None = None,
    ahora: datetime | None = None,
) -> None:
    """Los de /funding btc avisa: una vez al entrar en una de las dos puntas."""
    if _silenciado(config):
        return
    try:
        lista = database.get_funding(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer los avisos de funding: %s", e)
        return
    ahora = ahora or datetime.now(timezone.utc)

    def apuntar(v: funding.Vigilado, donde: str) -> None:
        try:
            database.guardar_funding(
                config.database_path, replace(v, extremo=donde, mirado=ahora)
            )
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar el funding de %s: %s", v.par, e)

    for v in lista:
        if v.coin_id in calladas or not funding.toca_mirar(v, ahora):
            continue
        try:
            datos = funding.leer(v.par, *funding.pedir(v.par))
        except funding.FundingError as e:
            logger.warning("No se pudo mirar el funding de %s: %s", v.par, e)
            datos = None
        if datos is None:
            # Apunto la hora igual: si Binance falla, no insisto en cada ciclo.
            apuntar(v, v.extremo)
            continue

        avisar, donde = funding.toca(v, datos)
        if not avisar:
            apuntar(v, donde)
        elif not _avisar(
            config,
            alerts.formatear_aviso_funding(datos),
            sueltos,
            partial(apuntar, v, donde),
        ):
            logger.error("No se pudo avisar del funding de %s", v.par)


def revisar_juntas(config: Config, sueltos: buzon.Buzon | None = None) -> None:
    """Las de /juntas: avisa cuando dos que iban a la vez se separan."""
    if _silenciado(config):
        return
    try:
        lista = database.get_juntas(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer las de /juntas: %s", e)
        return

    def apuntar(p: juntas.Pareja, avisada: bool) -> None:
        if avisada != p.avisada:
            database.guardar_juntas(config.database_path, replace(p, avisada=avisada))

    for p in lista:
        try:
            medida = _medir_pareja(config, p.una, p.otra)
        except database.DatabaseError as e:
            logger.error("Sin histórico para /juntas: %s", e)
            return
        avisar, avisada = juntas.toca(p, medida)
        if not avisar:
            apuntar(p, avisada)
        elif not _avisar(
            config,
            alerts.formatear_aviso_juntas(p, medida),
            sueltos,
            partial(apuntar, p, avisada),
        ):
            logger.error("No se pudo avisar de que %s y %s se separan", p.una, p.otra)


def revisar_salvo(
    config: Config,
    vigiladas: dict[str, float],
    calladas: set[str],
    sueltos: buzon.Buzon | None = None,
) -> None:
    """Con /mute ... salvo 10%: lo que se mueve mucho pasa aunque esté callado."""
    hasta = _silenciado(config)
    if hasta is None:
        return
    try:
        umbral = database.silencio_salvo(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudo leer el salvo del silencio: %s", e)
        return
    if umbral is None:
        return

    def apuntar(coin_id: str, cuando: datetime) -> None:
        logger.info("Aviso de %s aunque estoy callado", coin_id)
        try:
            database.guardar_salvo(config.database_path, coin_id, cuando)
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar el aviso de %s: %s", coin_id, e)

    ahora = datetime.now(timezone.utc)
    for coin_id, precio in vigiladas.items():
        # La que callaste a propósito sigue callada, aunque se hunda.
        if coin_id in calladas:
            continue
        variacion = _variacion(config, coin_id, precio)
        try:
            ultimo = database.ultimo_salvo(config.database_path, coin_id)
        except database.DatabaseError as e:
            logger.error("No se pudo leer el último aviso de %s: %s", coin_id, e)
            continue
        if not salvo.toca(variacion, umbral, ultimo, ahora):
            continue
        texto = salvo.texto(coin_id, precio, variacion, config.vs_currency, hasta)
        if not _avisar(config, texto, sueltos, partial(apuntar, coin_id, ahora)):
            logger.error("No se pudo avisar de %s aunque estoy callado", coin_id)


def _mandar_sueltos(config: Config, sueltos: buzon.Buzon) -> None:
    def mandar(texto: str) -> bool:
        return telegram.send_message(
            config.telegram_token,
            config.telegram_chat_id,
            texto,
            sin_sonido=_sin_sonido(config),
        )

    if not sueltos.entregar(mandar):
        # Nada se ha apuntado como avisado, así que salta otra vez el siguiente ciclo.
        logger.error("No se pudieron mandar %d avisos", len(sueltos.textos))
