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
import math
import sys
import time
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from crypto_tracker import (
    aceite,
    adios,
    adivina,
    airpods,
    ajustes,
    aleatoria,
    alerts,
    alquiler,
    aniversario,
    anual,
    apodo,
    arrepentido,
    ave,
    avisados,
    avisorsi,
    backup,
    bajon,
    ballena,
    bici,
    bigmac,
    boda,
    bola,
    botones,
    brusco,
    cafe,
    caida,
    calendario,
    callar,
    cana,
    caraocruz,
    carnet,
    cartera,
    chiste,
    churros,
    cine,
    coche,
    coingecko,
    comandos,
    comision,
    comparar,
    compensar,
    compras,
    concentracion,
    concierto,
    consejo,
    convertir,
    copia,
    corregir,
    correlacion,
    croquetas,
    cuando,
    cumple,
    cuota,
    dado,
    database,
    dato,
    dca,
    dia,
    diario,
    diasemana,
    doble,
    emoji,
    equilibrio,
    estables,
    ethereum,
    excusa,
    exportar,
    extremos,
    fifo,
    frase,
    futbol,
    galleta,
    ganancias,
    gasolina,
    gimnasio,
    grafica,
    halving,
    hodl,
    horas,
    horoscopo,
    hotel,
    hoy,
    hubiera,
    impuestos,
    iphone,
    jamon,
    kebab,
    lambo,
    libro,
    loteria,
    luz,
    macbook,
    maximo,
    media,
    mejor,
    mensual,
    menu,
    merge,
    mes,
    meta,
    metro,
    miedo,
    millonario,
    mitad,
    moneda,
    movimientos,
    mundo,
    navidad,
    netflix,
    nochevieja,
    nota,
    objetivo,
    oro,
    paella,
    pan,
    pelotazo,
    peluqueria,
    periodo,
    piso,
    pizza,
    ppt,
    primera,
    promediar,
    proximo,
    ps5,
    puntuales,
    quieta,
    quiz,
    racha,
    rango,
    ratio,
    rebalanceo,
    record,
    recordar,
    redondo,
    refran,
    rellenar,
    rentabilidad,
    reparto,
    riesgo,
    rolex,
    rsi,
    salud,
    sat,
    semanal,
    simbolos,
    sivendo,
    sofa,
    spotify,
    stop,
    sube,
    sueldo,
    supermercado,
    switch,
    tarot,
    taxi,
    telegram,
    tesla,
    top,
    tortilla,
    verdes,
    version,
    videojuego,
    vigiladas,
    volatilidad,
    vsbtc,
    vuelo,
    whitepaper,
    zapatillas,
)
from crypto_tracker.config import (
    Config,
    ConfigError,
    Posicion,
    load_config,
    minutos_mute,
)
from crypto_tracker.precio import en_sats

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
    pendientes = _caducar(config, _puntuales(config))
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
            nota=p.nota,
        )
        for p in hechas
    ]

    # Guardamos la zona de cada cripto para no repetir el aviso al reiniciar.
    try:
        database.save_state(config.database_path, estado_nuevo)
    except database.DatabaseError as e:
        logger.error("No se pudo guardar el estado de las alertas: %s", e)

    # Como con el /mute de todas: las de /alerta no se borran y saltan al volver.
    calladas = _calladas(config)
    revisar_bajon(config, valor, calladas)
    revisar_concentracion(config, precios, calladas)
    revisar_rsi(config, vigiladas, calladas)
    revisar_estables(config, list(precios), calladas)
    if calladas:
        avisos = [a for a in avisos if a.coin_id not in calladas]
        hechas = [p for p in hechas if p.coin_id not in calladas]

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

    maximos = _maximos_avisos(config, avisos)
    avisos = [
        replace(
            a,
            variacion_24h=_variacion(config, a.coin_id, a.price),
            falta_maximo=maximo.falta_a(maximos, a.coin_id, a.price),
        )
        for a in avisos
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
        _apuntar_avisos(config, avisos)
    else:
        # El aviso se perdio, pero el estado ya cambio. No insistimos:
        # el siguiente cruce volvera a avisar. Las de /alerta siguen ahi.
        logger.error("No se pudo avisar de: %s", cruzadas)

    return estado_nuevo, None


def _apuntar_avisos(config: Config, avisos: list[alerts.Alert]) -> None:
    """Para /ultimo. Solo los que han llegado, los del silencio no cuentan."""
    lista = [
        (a.coin_id, a.price, a.estado == alerts.ALTO)
        for a in avisos
        if a.coin_id != puntuales.CARTERA
    ]
    try:
        database.guardar_avisos(config.database_path, lista, datetime.now(timezone.utc))
    except database.DatabaseError as e:
        logger.error("No se pudo apuntar el aviso para /ultimo: %s", e)


def _maximos_avisos(
    config: Config, avisos: list[alerts.Alert]
) -> dict[str, maximo.Maximo]:
    """Una consulta para todos, y solo cuando hay aviso: casi ningún ciclo la gasta."""
    ids = [a.coin_id for a in avisos if a.coin_id != puntuales.CARTERA]
    if not ids:
        return {}
    try:
        return coingecko.maximos(list(dict.fromkeys(ids)), config.vs_currency)
    except coingecko.CoinGeckoError as e:
        # Es un extra; el aviso sale igual sin esa línea.
        logger.warning("Aviso sin el máximo histórico: %s", e)
        return {}


def _calladas(config: Config) -> set[str]:
    try:
        return set(database.criptos_calladas(config.database_path))
    except database.DatabaseError as e:
        # Mejor algun aviso de mas que quedarse sin ninguno.
        logger.error("No se pudo leer que criptos estan calladas: %s", e)
        return set()


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


def _caducar(
    config: Config, pendientes: list[puntuales.Puntual]
) -> list[puntuales.Puntual]:
    """Quita las de /alerta que han caducado sin saltar, y te lo dice."""
    # Callado no: como las que saltan, que esperen a que vuelvas.
    if _silenciado(config):
        return pendientes
    viejas = puntuales.caducadas(pendientes, datetime.now(timezone.utc))
    calladas = _calladas(config)
    viejas = [p for p in viejas if p.coin_id not in calladas]
    if not viejas:
        return pendientes

    if telegram.send_message(
        config.telegram_token,
        config.telegram_chat_id,
        alerts.formatear_caducadas(viejas, config.vs_currency),
        sin_sonido=True,
    ):
        logger.info("Caducadas: %s", ", ".join(str(p.id) for p in viejas))
        _borrar_puntuales(config, viejas)
    # Si no ha llegado el mensaje, el siguiente ciclo lo vuelve a intentar.
    return [p for p in pendientes if p not in viejas]


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


def revisar_bajon(config: Config, valor: float | None, calladas: set[str]) -> None:
    """Avisa si la cartera ha caído CAIDA_CARTERA desde su récord. Va aparte."""
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
    if not telegram.send_message(
        config.telegram_token,
        config.telegram_chat_id,
        texto,
        sin_sonido=_sin_sonido(config),
    ):
        logger.error("No se pudo avisar de la caída de la cartera")
        return

    logger.info("Aviso de caída de la cartera: %.2f%%", resultado.caida)
    try:
        database.guardar_bajon(config.database_path, resultado.cuando, escalon)
    except database.DatabaseError as e:
        logger.error("No se pudo apuntar el aviso de caída de la cartera: %s", e)


def revisar_concentracion(
    config: Config, precios: dict[str, float], calladas: set[str]
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

    c = concentracion.mayor(valores)
    if not concentracion.toca(c, config.concentracion, avisado):
        nuevo = concentracion.sigue(c, config.concentracion, avisado)
    elif telegram.send_message(
        config.telegram_token,
        config.telegram_chat_id,
        alerts.formatear_concentracion(c),
        sin_sonido=_sin_sonido(config),
    ):
        logger.info("Aviso de concentración: %s es el %.1f%%", c.coin_id, c.peso)
        nuevo = c.coin_id
    else:
        logger.error("No se pudo avisar de la concentración de la cartera")
        return

    if nuevo == avisado:
        return
    try:
        database.guardar_concentracion(config.database_path, nuevo)
    except database.DatabaseError as e:
        logger.error("No se pudo apuntar el aviso de concentración: %s", e)


def revisar_estables(config: Config, coin_ids: list[str], calladas: set[str]) -> None:
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

    salen, vuelven = estables.revisar(precios_usd, avisadas)
    for d in salen + vuelven:
        fuera = d in salen
        # Si no llega, no se apunta y lo intenta el siguiente ciclo.
        if not telegram.send_message(
            config.telegram_token,
            config.telegram_chat_id,
            alerts.formatear_estable(d, vuelve=not fuera),
            sin_sonido=_sin_sonido(config),
        ):
            logger.error("No se pudo avisar de %s", d.simbolo)
            continue
        logger.info("%s a $%.4f", d.simbolo, d.precio)
        try:
            database.guardar_estable(config.database_path, d.coin_id, fuera)
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar el aviso de %s: %s", d.simbolo, e)


def revisar_rsi(
    config: Config, vigiladas: dict[str, float], calladas: set[str]
) -> None:
    """Avisa una vez cuando una que vigilas entra en sobrecompra o sobreventa."""
    if not config.aviso_rsi or _silenciado(config):
        return

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
            nueva = avisorsi.sigue(resultado.valor, avisado)
        elif telegram.send_message(
            config.telegram_token,
            config.telegram_chat_id,
            alerts.formatear_aviso_rsi(coin_id, resultado, config.vs_currency),
            sin_sonido=_sin_sonido(config),
        ):
            logger.info("Aviso de RSI: %s en %.0f", coin_id, resultado.valor)
            nueva = zona
        else:
            logger.error("No se pudo avisar del RSI de %s", coin_id)
            continue

        if nueva == avisado:
            continue
        try:
            database.guardar_zona_rsi(config.database_path, coin_id, nueva)
        except database.DatabaseError as e:
            logger.error("No se pudo apuntar el aviso de RSI de %s: %s", coin_id, e)


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
            resumen_mensual(config)
            resumen_anual(config)
            recordatorios(config)
            copia_semanal(config)
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
            len(_puntuales(config)),
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


SIN_CARTERA = (
    "No tienes cartera puesta. Apunta lo que tienes con "
    "/compra bitcoin 0.016 1000, o añade al .env algo como:\n"
    "<code>PORTFOLIO=bitcoin:0.016:1000</code>"
)


def responder(
    config: Config, nombre: str, argumento: str
) -> str | comandos.Foto | comandos.Archivo | comandos.ConBotones:
    """El texto con el que se contesta a cada comando."""
    if nombre == "ayuda":
        return comandos.ayuda(argumento)

    if nombre == "status":
        texto = montar_resumen(config)
        if texto is None:
            return "No he podido consultar los precios. Prueba en un rato."
        return comandos.ConBotones(texto, botones.actualizar("/status"))

    if nombre == "resumen":
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

    if nombre == "mute":
        if not argumento:
            # A secas, si ya estaba callado, mejor decirlo que alargarlo sin querer.
            estaba = database.silenciado_hasta(config.database_path)
            calladas = database.criptos_calladas(config.database_path)
            return comandos.ConBotones(
                callar.a_secas(estaba, calladas),
                botones.para_mute(ya_callado=bool(estaba or calladas)),
            )
        try:
            cripto, minutos = callar.interpretar(argumento, datetime.now().astimezone())
        except ConfigError as e:
            return str(e)
        hasta = datetime.now(timezone.utc) + timedelta(minutes=minutos)
        if cripto:
            database.callar_cripto(config.database_path, cripto, hasta)
            return (
                f"🔕 No te aviso de <b>{telegram.escape(cripto)}</b> hasta las "
                f"{hasta.astimezone():%H:%M del %d/%m} "
                f"({salud.cuanto(timedelta(minutes=minutos))}). "
                f"Las demás siguen avisando. Para deshacerlo, /unmute {cripto}"
            )
        database.silenciar_hasta(config.database_path, hasta)
        return comandos.ConBotones(
            f"🔕 Callado hasta las {hasta.astimezone():%H:%M del %d/%m} "
            f"({salud.cuanto(timedelta(minutes=minutos))}).",
            botones.deshacer_mute(),
        )

    if nombre == "unmute":
        if argumento:
            cripto = simbolos.a_id(argumento)
            if cripto not in database.criptos_calladas(config.database_path):
                return f"No tenía callada <b>{telegram.escape(cripto)}</b>."
            database.callar_cripto(config.database_path, cripto, None)
            return f"🔔 Vuelvo a avisar de <b>{telegram.escape(cripto)}</b>."

        estaba = database.silenciado_hasta(config.database_path)
        calladas = database.criptos_calladas(config.database_path)
        database.silenciar_hasta(config.database_path, None)
        database.descallar_todas(config.database_path)
        return "🔔 Vuelvo a avisar." if estaba or calladas else "No estaba callado."

    if nombre == "horario":
        return _horario(config, argumento)

    if nombre == "semana":
        # De una sola es lo mismo que su histórico de 7 días: no lo duplico.
        if len(argumento.split()) > 1:
            return "De una en una. Por ejemplo: /semana bitcoin"
        if argumento:
            return _historico(config, f"{argumento} 7d")
        return _semana(config)

    if nombre == "cartera":
        config = _con_cambios(config)
        if not config.cartera:
            return SIN_CARTERA
        return _cartera(config, argumento)

    if nombre == "reparto":
        config = _con_cambios(config)
        if not config.cartera:
            return SIN_CARTERA
        return _reparto(config)

    if nombre == "riesgo":
        config = _con_cambios(config)
        if not config.cartera:
            return SIN_CARTERA
        return _riesgo(config)

    if nombre == "rebalanceo":
        config = _con_cambios(config)
        if not config.cartera:
            return SIN_CARTERA
        return _rebalanceo(config, argumento)

    if nombre == "compra":
        return _comprar(config, argumento)

    if nombre == "venta":
        return _vender(config, argumento)

    if nombre == "recompensa":
        return _recompensa(config, argumento)

    if nombre == "corregir":
        return _corregir(config, argumento)

    if nombre == "movimientos":
        return _movimientos(config, argumento)

    if nombre == "primera":
        return _primera(config, argumento)

    if nombre == "pelotazo":
        return _pelotazo(config)

    if nombre == "apodo":
        return _apodo(config)

    if nombre == "ganancias":
        return _ganancias(config)

    if nombre == "arrepentido":
        return _arrepentido(config)

    if nombre == "impuestos":
        return _impuestos(config, argumento)

    if nombre == "sivendo":
        return _sivendo(config, argumento)

    if nombre == "compensar":
        return _compensar(config)

    if nombre == "deshacer":
        return _deshacer(config, argumento)

    if nombre == "historico":
        return _historico(config, argumento)

    if nombre == "alerta":
        return _crear_alerta(config, argumento)

    if nombre == "recordar":
        return _recordar(config, argumento)

    if nombre == "stop":
        config = _con_cambios(config)
        if not config.cartera:
            return SIN_CARTERA
        return _stop(config, argumento)

    if nombre == "vigilar":
        return _vigilar(config, argumento) if argumento else _lista_vigiladas(config)

    if nombre == "dejar":
        return _dejar(config, simbolos.varias(argumento))

    if nombre == "alertas":
        return _alertas(config)

    if nombre == "quitar":
        # A secas, la lista con sus 🗑: mas facil que ir a mirar el numero.
        if not argumento:
            return _alertas(config)
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
            if len(argumento.split()) == 1:
                return _quitar_de_cripto(config, simbolos.a_id(argumento))
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
        apuntar_consultas(config)
        ahora = datetime.now(timezone.utc)
        return salud.mensaje_bot(
            _pulso,
            ahora,
            len(_con_cambios(config).watchlist),
            len(database.get_puntuales(config.database_path, config.vs_currency)),
            _silenciado(config),
            database.get_consultas(config.database_path, cuota.mes(ahora)),
            database.guardados(config.database_path),
        )

    if nombre == "precio":
        return _precio(config, argumento)

    if nombre == "convertir":
        return _convertir(config, argumento)

    if nombre == "exportar":
        return _exportar(config, argumento)

    if nombre == "si":
        return _si(config, argumento)

    if nombre == "dca":
        return _dca(config, argumento)

    if nombre == "objetivo":
        return _objetivo(config, argumento)

    if nombre == "promediar":
        return _promediar(config, argumento)

    if nombre == "meta":
        return _meta(config, argumento)

    if nombre == "mes":
        return _mes(config)

    if nombre == "anual":
        return _anual(config, argumento)

    if nombre == "hodl":
        return _hodl(config)

    if nombre == "record":
        return _record(config)

    if nombre == "vsbtc":
        return _vsbtc(config)

    if nombre == "compras":
        return _compras(config, argumento)

    if nombre == "calendario":
        return _calendario(config, argumento)

    if nombre == "rentabilidad":
        return _rentabilidad(config)

    if nombre == "ath":
        return _ath(config, argumento)

    if nombre == "tendencias":
        return _tendencias(config)

    if nombre == "mercado":
        return _mercado(config)

    if nombre == "top":
        return _top(config)

    if nombre == "aleatoria":
        return _aleatoria(config)

    if nombre == "glosario":
        return alerts.formatear_glosario(argumento)

    if nombre == "frase":
        return alerts.formatear_frase(frase.elegir())

    if nombre == "consejo":
        return alerts.formatear_consejo(consejo.elegir())

    if nombre == "excusa":
        return alerts.formatear_excusa(excusa.elegir())

    if nombre == "refran":
        return alerts.formatear_refran(refran.elegir())

    if nombre == "horoscopo":
        try:
            signo = horoscopo.interpretar(argumento)
        except horoscopo.HoroscopoError as e:
            return telegram.escape(str(e))
        return alerts.formatear_horoscopo(horoscopo.leer(signo, date.today()))

    if nombre == "galleta":
        return alerts.formatear_galleta(galleta.abrir(date.today()))

    if nombre == "tarot":
        return alerts.formatear_tarot(tarot.sacar())

    if nombre == "bola":
        try:
            pregunta = bola.interpretar(argumento)
        except bola.BolaError as e:
            return telegram.escape(str(e))
        return alerts.formatear_bola(pregunta, bola.agitar())

    if nombre == "version":
        return alerts.formatear_version(version.leer())

    if nombre == "chiste":
        return alerts.formatear_chiste(chiste.elegir())

    if nombre == "dato":
        return alerts.formatear_dato(dato.elegir())

    if nombre == "dado":
        # Lee la cripto igual que /caraocruz, así que uso su misma función.
        return alerts.formatear_dado(dado.tirar(), caraocruz.interpretar(argumento))

    if nombre == "caraocruz":
        return alerts.formatear_caraocruz(
            caraocruz.lanzar(), caraocruz.interpretar(argumento)
        )

    if nombre == "adivina":
        return _adivina(config, argumento)

    if nombre == "quiz":
        elegida = quiz.interpretar(argumento)
        if elegida is None:
            return comandos.ConBotones(*alerts.formatear_quiz(quiz.sacar()))
        return comandos.ConBotones(*alerts.formatear_respuesta_quiz(*elegida))

    if nombre == "ppt":
        try:
            tuya = ppt.interpretar(argumento)
        except ppt.PptError as e:
            return telegram.escape(str(e))
        del_bot = ppt.sacar()
        return alerts.formatear_ppt(tuya, del_bot, ppt.resultado(tuya, del_bot))

    if nombre == "ultimo":
        return _ultimo(config)

    if nombre == "miedo":
        return _miedo()

    if nombre == "comparar":
        return _comparar(config, argumento)

    if nombre == "quieta":
        return _quieta(config)

    if nombre == "volatilidad":
        return _volatilidad(config, argumento)

    if nombre == "rango":
        return _rango(config, argumento)

    if nombre == "racha":
        return _racha(config, argumento)

    if nombre == "caida":
        return _caida(config, argumento)

    if nombre == "sube":
        return _sube(config, argumento)

    if nombre == "verdes":
        return _verdes(config, argumento)

    if nombre == "extremo":
        return _extremo(config, argumento)

    if nombre == "diasemana":
        return _diasemana(config, argumento)

    if nombre == "horas":
        return _horas(config, argumento)

    if nombre == "ratio":
        return _ratio(config, argumento)

    if nombre == "hoy":
        return _hoy(config, argumento)

    if nombre == "equilibrio":
        return _equilibrio(config)

    if nombre == "doble":
        return _doble(config)

    if nombre == "mitad":
        return _mitad(config)

    if nombre == "rsi":
        return _rsi(config, argumento)

    if nombre == "rellenar":
        return _rellenar(config, argumento)

    if nombre == "backup":
        return _backup(config)

    if nombre == "cuando":
        return _cuando(config, argumento)

    if nombre == "redondo":
        return _redondo(config, argumento)

    if nombre == "dia":
        return _dia(config, argumento)

    if nombre == "correlacion":
        return _correlacion(config, argumento)

    if nombre == "halving":
        return alerts.formatear_halving(halving.calcular(date.today()))

    if nombre == "pizza":
        return _pizza(config)

    if nombre == "mundo":
        return _mundo(config)

    if nombre == "lambo":
        return _lambo(config)

    if nombre == "enletras":
        valor = _valor_guardado(config)
        if isinstance(valor, str):
            return valor
        return alerts.formatear_enletras(valor, config.vs_currency)

    if nombre == "ballena":
        return _ballena(config)

    if nombre == "cafe":
        return _cafe(config)

    if nombre == "sueldo":
        return _sueldo(config)

    if nombre == "gasolina":
        return _gasolina(config)

    if nombre == "bigmac":
        return _bigmac(config)

    if nombre == "iphone":
        return _iphone(config)

    if nombre == "alquiler":
        return _alquiler(config)

    if nombre == "oro":
        return _oro(config)

    if nombre == "netflix":
        return _netflix(config)

    if nombre == "ps5":
        return _ps5(config)

    if nombre == "tesla":
        return _tesla(config)

    if nombre == "spotify":
        return _spotify(config)

    if nombre == "cana":
        return _cana(config)

    if nombre == "switch":
        return _switch(config)

    if nombre == "cine":
        return _cine(config)

    if nombre == "gimnasio":
        return _gimnasio(config)

    if nombre == "vuelo":
        return _vuelo(config)

    if nombre == "super":
        return _super(config)

    if nombre == "kebab":
        return _kebab(config)

    if nombre == "metro":
        return _metro(config)

    if nombre == "luz":
        return _luz(config)

    if nombre == "libro":
        return _libro(config)

    if nombre == "concierto":
        return _concierto(config)

    if nombre == "airpods":
        return _airpods(config)

    if nombre == "zapatillas":
        return _zapatillas(config)

    if nombre == "ave":
        return _ave(config)

    if nombre == "menu":
        return _menu(config)

    if nombre == "hotel":
        return _hotel(config)

    if nombre == "peluqueria":
        return _peluqueria(config)

    if nombre == "macbook":
        return _macbook(config)

    if nombre == "bici":
        return _bici(config)

    if nombre == "churros":
        return _churros(config)

    if nombre == "loteria":
        return _loteria(config)

    if nombre == "piso":
        return _piso(config)

    if nombre == "futbol":
        return _futbol(config)

    if nombre == "taxi":
        return _taxi(config)

    if nombre == "tortilla":
        return _tortilla(config)

    if nombre == "videojuego":
        return _videojuego(config)

    if nombre == "sofa":
        return _sofa(config)

    if nombre == "coche":
        return _coche(config)

    if nombre == "boda":
        return _boda(config)

    if nombre == "jamon":
        return _jamon(config)

    if nombre == "aceite":
        return _aceite(config)

    if nombre == "paella":
        return _paella(config)

    if nombre == "croquetas":
        return _croquetas(config)

    if nombre == "pan":
        return _pan(config)

    if nombre == "rolex":
        return _rolex(config)

    if nombre == "emoji":
        return _emoji(config)

    if nombre == "tiempo":
        return _tiempo(config)

    if nombre == "carnet":
        return _carnet(config)

    if nombre == "nochevieja":
        return _nochevieja(config)

    if nombre == "navidad":
        return _navidad(config)

    if nombre == "cumple":
        return alerts.formatear_cumple(cumple.Cumple(date.today()))

    if nombre == "whitepaper":
        return alerts.formatear_whitepaper(whitepaper.Whitepaper(date.today()))

    if nombre == "merge":
        return alerts.formatear_merge(merge.Merge(date.today()))

    if nombre == "ethereum":
        return alerts.formatear_ethereum(ethereum.Ethereum(date.today()))

    if nombre == "adios":
        return alerts.formatear_adios(adios.Adios(date.today()))

    if nombre == "millonario":
        return _millonario(config, argumento)

    if nombre == "sat":
        precio = _precio_o_pedirlo(config, "bitcoin")
        if isinstance(precio, str):
            return precio
        return alerts.formatear_sat(sat.Sat(precio), config.vs_currency)

    if nombre == "ajustes":
        return ajustes.mensaje(_con_cambios(config))

    if nombre == "copia":
        actual = _con_cambios(config)
        return alerts.formatear_copia(
            copia.lineas(actual.watchlist, actual.cartera, actual.resumen_diario)
        )

    if nombre == "media":
        return _media(config, argumento)

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

    return comandos.no_entiendo(nombre, telegram.escape(argumento))


def _horario(config: Config, argumento: str) -> str:
    if not argumento:
        hora = _con_cambios(config).resumen_diario
        if hora is None:
            return "Ahora no te mando resumen. Para ponerlo: /horario 9:00"
        return (
            f"☀️ Te mando el resumen cada día a las <b>{hora:%H:%M}</b>.\n"
            "Para cambiarla: /horario 8:30. Para quitarlo: /horario no"
        )

    try:
        hora = diario.leer_hora(argumento)
    except ConfigError as e:
        return telegram.escape(str(e))
    database.guardar_hora_resumen(config.database_path, hora)
    if hora is None:
        return "🔕 Ya no te mando el resumen del día. Para volver: /horario 9:00"
    return f"☀️ Hecho, te mando el resumen cada día a las <b>{hora:%H:%M}</b>."


def _alertas(config: Config) -> str | comandos.ConBotones:
    pendientes = database.get_puntuales(config.database_path, config.vs_currency)
    precios = _precios_alertas(config, pendientes)
    pendientes = puntuales.por_cercania(pendientes, precios)
    texto = alerts.formatear_puntuales(pendientes, config.vs_currency, precios)
    if precios:
        texto = alerts.con_fuente(texto)
    if not pendientes:
        return texto
    return comandos.ConBotones(texto, botones.para_alertas(pendientes))


def _quitar_de_cripto(config: Config, coin_id: str) -> str:
    """/quitar bitcoin: todas las de esa cripto de una vez."""
    pendientes = database.get_puntuales(config.database_path, config.vs_currency)
    numeros = puntuales.de_cripto(pendientes, coin_id)
    if not numeros:
        return f"No tienes ninguna alerta de {telegram.escape(coin_id)}. Mira /alertas"
    for n in numeros:
        database.borrar_puntual(config.database_path, n)
    return alerts.formatear_quitadas(numeros, [])


def _lista_vigiladas(config: Config) -> str | comandos.ConBotones:
    cambios = database.get_cambios(config.database_path)
    desde_telegram = {c for c, regla in cambios.items() if regla is not None}
    watchlist = _con_cambios(config).watchlist
    texto = alerts.formatear_vigiladas(watchlist, config.vs_currency, desde_telegram)
    teclado = botones.para_vigilar([w.coin_id for w in watchlist])
    return comandos.ConBotones(texto, teclado) if teclado else texto


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


def _dejar(config: Config, coin_ids: list[str]) -> str:
    if not coin_ids:
        return "¿Cuál? Por ejemplo: /dejar solana o /dejar sol eth"

    actuales = [w.coin_id for w in _con_cambios(config).watchlist]
    quitar = [c for c in coin_ids if c in actuales]
    no_estan = [c for c in coin_ids if c not in actuales]
    if not quitar:
        return f"No estoy vigilando {_en_negrita(no_estan, 'ni')}. Mira /vigilar"
    # O todas o ninguna: quitar solo algunas sin que lo pidas seria peor.
    if len(quitar) == len(actuales):
        if len(actuales) == 1:
            return (
                "Es la única que vigilo. Si la quito no te avisaría de nada. "
                "Añade otra antes con /vigilar."
            )
        return (
            "Son todas las que vigilo. Si las quito no te avisaría de nada. "
            "Deja alguna o añade otra antes con /vigilar."
        )

    for coin_id in quitar:
        database.guardar_cambio(config.database_path, coin_id, None)
        logger.info("Watchlist: deja de vigilar %s", coin_id)
    nombres = [c.replace("-", " ").title() for c in quitar]
    texto = f"👋 Dejo de vigilar {_en_negrita(nombres, 'y')}."
    if no_estan:
        texto += f"\nNo estaba vigilando {_en_negrita(no_estan, 'ni')}."
    return texto


def _en_negrita(nombres: list[str], ultimo: str) -> str:
    """['a', 'b', 'c'] -> '<b>a</b>, <b>b</b> y <b>c</b>'."""
    partes = [f"<b>{telegram.escape(n)}</b>" for n in nombres]
    if len(partes) == 1:
        return partes[0]
    return f"{', '.join(partes[:-1])} {ultimo} {partes[-1]}"


def _comprar(config: Config, argumento: str) -> str | comandos.ConBotones:
    try:
        argumento, apunte = nota.separar(argumento)
        argumento, texto_comision = comision.separar(argumento)
        coin_id, cantidad, coste = movimientos.interpretar_compra(argumento)
    except movimientos.MovimientoError as e:
        return telegram.escape(str(e))

    antes = movimientos.buscar(_con_cambios(config).cartera, coin_id)
    # Sin coste hace falta el precio de ahora; si es nueva, de paso vemos que existe.
    # Si no, solo sirve para pillar erratas, y sin el se apunta igual.
    imprescindible = coste is None or antes is None
    try:
        precio = coingecko.get_prices([coin_id], config.vs_currency).get(coin_id)
    except coingecko.CoinGeckoError as e:
        if imprescindible:
            return f"No he podido consultar el precio: {telegram.escape(str(e))}"
        precio = None
    if precio is None and imprescindible:
        return (
            f"No encuentro <b>{telegram.escape(coin_id)}</b> en CoinGecko. "
            f"Prueba con /buscar {telegram.escape(coin_id)}"
        )
    if coste is None:
        coste = cantidad * precio
    pagada = None
    if texto_comision:
        try:
            pagada = comision.calcular(texto_comision, coste)
        except comision.ComisionError as e:
            return telegram.escape(str(e))
        # Va dentro de lo que te costó: si no, el precio medio te saldría más bajo.
        coste += pagada

    ahora = movimientos.comprar(antes, coin_id, cantidad, coste)
    numero = database.apuntar_movimiento(
        config.database_path, coin_id, "compra", cantidad, coste, antes, ahora, apunte
    )
    logger.info("Cartera: compra %s de %s por %s", cantidad, coin_id, coste)
    return comandos.ConBotones(
        alerts.formatear_compra(
            cantidad,
            coste,
            ahora,
            config.vs_currency,
            antes,
            precio,
            pagada,
            apunte,
        ),
        botones.deshacer_movimiento(numero),
    )


def _vender(config: Config, argumento: str) -> str | comandos.ConBotones:
    try:
        argumento, apunte = nota.separar(argumento)
        argumento, texto_comision = comision.separar(argumento)
        coin_id, cantidad, precio = movimientos.interpretar_venta(argumento)
        antes = movimientos.buscar(_con_cambios(config).cartera, coin_id)
        queda = movimientos.vender(antes, coin_id, cantidad)
        vendido = antes.cantidad if cantidad is None else cantidad
        cobrado = movimientos.cobrado(precio, vendido) if precio else None
    except movimientos.MovimientoError as e:
        return telegram.escape(str(e))

    if cobrado is None:
        cobrado = _cobrado_ahora(config, coin_id, vendido)
    pagada = None
    # Sin saber lo que te dieron no hay de dónde restarla: se apunta sin ella.
    if texto_comision and cobrado is not None:
        try:
            pagada = comision.calcular(texto_comision, cobrado)
            cobrado = comision.de_venta(cobrado, pagada)
        except comision.ComisionError as e:
            return telegram.escape(str(e))
    numero = database.apuntar_movimiento(
        config.database_path, coin_id, "venta", vendido, cobrado, antes, queda, apunte
    )
    logger.info("Cartera: vende %s de %s por %s", vendido, coin_id, cobrado)
    return comandos.ConBotones(
        alerts.formatear_venta(
            coin_id,
            vendido,
            queda,
            config.vs_currency,
            cobrado,
            ganancias.de_venta(antes, vendido, cobrado),
            pagada,
            apunte,
        ),
        botones.deshacer_movimiento(numero),
    )


def _recompensa(config: Config, argumento: str) -> str | comandos.ConBotones:
    try:
        argumento, apunte = nota.separar(argumento)
        coin_id, cantidad, valor = movimientos.interpretar_recompensa(argumento)
    except movimientos.MovimientoError as e:
        return telegram.escape(str(e))

    if valor is None:
        # Consulta y no el último guardado: este valor se queda para Hacienda.
        try:
            precio = coingecko.get_prices([coin_id], config.vs_currency).get(coin_id)
        except coingecko.CoinGeckoError as e:
            return f"No he podido consultar el precio: {telegram.escape(str(e))}"
        if precio is None:
            return alerts.formatear_no_encuentro([coin_id])
        valor = cantidad * precio

    antes = movimientos.buscar(_con_cambios(config).cartera, coin_id)
    ahora = movimientos.comprar(antes, coin_id, cantidad, valor)
    numero = database.apuntar_movimiento(
        config.database_path,
        coin_id,
        "recompensa",
        cantidad,
        valor,
        antes,
        ahora,
        apunte,
    )
    logger.info("Cartera: recompensa de %s de %s", cantidad, coin_id)
    return comandos.ConBotones(
        alerts.formatear_recompensa(cantidad, valor, ahora, config.vs_currency, apunte),
        botones.deshacer_movimiento(numero),
    )


def _cobrado_ahora(config: Config, coin_id: str, vendido: float) -> float | None:
    """Sin decir a cuánto, al precio de ahora, como /compra."""
    try:
        precios = coingecko.get_prices([coin_id], config.vs_currency)
    except coingecko.CoinGeckoError as e:
        # La venta se apunta igual; solo se queda fuera de /ganancias.
        logger.warning("Apunto la venta sin precio: %s", e)
        return None
    precio = precios.get(coin_id)
    return None if precio is None else precio * vendido


def _ganancias(config: Config) -> str:
    ventas = database.get_ventas(config.database_path)
    return alerts.formatear_ganancias(ganancias.calcular(ventas), config.vs_currency)


def _arrepentido(config: Config) -> str:
    ventas = database.get_ventas(config.database_path)
    coin_ids = list(dict.fromkeys(v.coin_id for v in ventas if v.coste is not None))
    precios = {}
    if coin_ids:
        precios = _consultar(config, coin_ids)
        if precios is None:
            return "No he podido consultar los precios. Prueba en un rato."
    resultado = arrepentido.calcular(ventas, precios)
    return alerts.formatear_arrepentido(resultado, config.vs_currency)


def _impuestos(config: Config, argumento: str) -> str:
    try:
        año = impuestos.interpretar(argumento, date.today().year)
    except impuestos.ImpuestosError as e:
        return telegram.escape(str(e))
    todos = database.get_movimientos(config.database_path, None)
    return alerts.formatear_impuestos(
        impuestos.calcular(todos, año),
        config.vs_currency,
        impuestos.recompensas_de(todos, año),
    )


def _sivendo(config: Config, argumento: str) -> str:
    try:
        coin_id, cantidad, precio = sivendo.interpretar(argumento)
        antes = movimientos.buscar(_con_cambios(config).cartera, coin_id)
        queda = movimientos.vender(antes, coin_id, cantidad)
    except movimientos.MovimientoError as e:
        return telegram.escape(str(e))

    vendido = antes.cantidad if cantidad is None else cantidad
    if precio:
        dinero = movimientos.cobrado(precio, vendido)
    else:
        ahora = _precio_o_pedirlo(config, coin_id)
        if isinstance(ahora, str):
            return ahora
        dinero = ahora * vendido

    todos = database.get_movimientos(config.database_path, None)
    este_año = impuestos.calcular(todos, date.today().year)
    historia = [m for m in todos if m.coin_id == coin_id]
    return alerts.formatear_sivendo(
        sivendo.calcular(antes, vendido, dinero, queda, este_año, historia),
        config.vs_currency,
    )


def _compensar(config: Config) -> str:
    hoy = date.today()
    todos = database.get_movimientos(config.database_path, None)
    este_año = impuestos.calcular(todos, hoy.year)
    cartera = _con_cambios(config).cartera

    precios = {}
    # Sin ganancia no hay nada que compensar y no merece gastar una consulta.
    if este_año.ganancia > 0 and cartera:
        try:
            precios = coingecko.get_prices(
                [p.coin_id for p in cartera], config.vs_currency
            )
        except coingecko.CoinGeckoError as e:
            return f"No he podido mirar los precios: {telegram.escape(str(e))}"

    plan = compensar.calcular(este_año, fifo.lotes(todos, cartera), precios)
    return alerts.formatear_compensar(plan, config.vs_currency, hoy)


def _deshacer(config: Config, argumento: str) -> str:
    try:
        numero = movimientos.interpretar_deshacer(argumento)
    except movimientos.MovimientoError as e:
        return telegram.escape(str(e))

    ultimos = database.get_movimientos(config.database_path, 1)
    # Los numeros no se repiten, asi que uno mayor que el ultimo ya se deshizo.
    if numero is not None and (not ultimos or numero > ultimos[0].id):
        return "Esa ya está deshecha. Mira /movimientos"
    if not ultimos:
        return "No hay ninguna compra ni venta que deshacer. Mira /movimientos"
    # Solo la ultima: deshacer una de en medio dejaria mal las que van detras.
    if numero is not None and ultimos[0].id != numero:
        return (
            "Esa ya no es la última, has apuntado otras después. "
            "Mira /movimientos y deshaz primero la de arriba."
        )

    hecho = database.deshacer_ultimo(config.database_path)
    logger.info("Cartera: deshace la %s de %s", hecho.tipo, hecho.coin_id)
    return alerts.formatear_deshecho(hecho, config.vs_currency)


def _corregir(config: Config, argumento: str) -> str:
    try:
        numero, campo, texto = corregir.interpretar(argumento)
    except movimientos.MovimientoError as e:
        return telegram.escape(str(e))

    todos = database.get_movimientos(config.database_path, None)
    elegido = next((m for m in todos if m.id == numero), None)
    if elegido is None:
        return f"No tengo el movimiento #{numero}. Mira /movimientos"

    historia = [m for m in todos if m.coin_id == elegido.coin_id]
    actual = movimientos.buscar(_con_cambios(config).cartera, elegido.coin_id)
    try:
        correccion = corregir.calcular(historia, numero, campo, texto, actual)
    except movimientos.MovimientoError as e:
        return telegram.escape(str(e))

    database.reescribir_movimientos(
        config.database_path, elegido.coin_id, correccion.historia, correccion.final
    )
    logger.info("Cartera: corrige el movimiento %s (%s)", numero, campo)
    return alerts.formatear_corregido(correccion, config.vs_currency)


def _movimientos(config: Config, argumento: str) -> str | comandos.ConBotones:
    coin_id = simbolos.a_id(argumento) if argumento else None
    lista = database.get_movimientos(config.database_path, coin_id=coin_id)
    todos = database.get_movimientos(config.database_path, None, coin_id)
    texto = alerts.formatear_movimientos(lista, config.vs_currency, coin_id, todos)
    if not lista:
        return texto
    # /deshacer solo quita la ultima de todas, que puede ser de otra cripto.
    ultima = database.get_movimientos(config.database_path, 1)[0]
    if lista[0].id != ultima.id:
        return texto
    return comandos.ConBotones(
        texto, botones.deshacer_movimiento(lista[0].id, "↩️ Deshacer la última")
    )


def _primera(config: Config, argumento: str) -> str:
    coin_id = simbolos.a_id(argumento) if argumento else None
    todos = database.get_movimientos(config.database_path, None, coin_id)
    compra = primera.buscar(todos)
    if compra is None:
        de = f" de <b>{telegram.escape(coin_id)}</b>" if coin_id else ""
        return (
            f"No has apuntado ninguna compra{de} por aquí. Lo del PORTFOLIO "
            f"del .env no sale. Apúntala así: {movimientos.EJEMPLO_COMPRA}"
        )
    # Sin precio sale igual, solo sin la comparación.
    precios = _consultar(config, [compra.coin_id]) or {}
    resultado = primera.Primera(compra, precios.get(compra.coin_id), date.today())
    texto = alerts.formatear_primera(resultado, config.vs_currency)
    return alerts.con_fuente(texto) if resultado.precio is not None else texto


def _pelotazo(config: Config) -> str:
    todos = database.get_movimientos(config.database_path, None)
    coin_ids = list(dict.fromkeys(m.coin_id for m in todos if m.tipo == "compra"))
    precios = {}
    if coin_ids:
        precios = _consultar(config, coin_ids)
        if precios is None:
            return "No he podido consultar los precios. Prueba en un rato."
    return alerts.formatear_pelotazo(
        pelotazo.calcular(todos, precios), config.vs_currency
    )


def _apodo(config: Config) -> str:
    posiciones = list(_con_cambios(config).cartera)
    todos = database.get_movimientos(config.database_path, None)
    compras = [m for m in todos if m.tipo == "compra"]
    dias = None
    if compras:
        primera = min(m.cuando for m in compras)
        dias = (date.today() - primera.astimezone().date()).days

    cambio = None
    if posiciones:
        valores, faltan = cartera.valorar(
            posiciones, _precios_guardados(config, posiciones)
        )
        # Sin el precio de alguna, el % sería de otra cartera.
        if not faltan:
            cambio = cartera.total(valores).porcentaje

    perfil = apodo.Perfil(
        criptos=sorted(p.coin_id for p in posiciones),
        compras=len(compras),
        ventas=sum(1 for m in todos if m.tipo == "venta"),
        dias=dias,
        cambio=cambio,
    )
    return alerts.formatear_apodo(apodo.elegir(perfil))


def _hodl(config: Config) -> str:
    posiciones = list(_con_cambios(config).cartera)
    if not posiciones:
        return SIN_CARTERA
    todos = database.get_movimientos(config.database_path, None)
    lista, sin_fecha = hodl.calcular(posiciones, todos, date.today())
    if not lista:
        return (
            "No sé desde cuándo tienes nada: lo del PORTFOLIO del .env no lleva "
            f"fecha. Apunta lo que compres así: {movimientos.EJEMPLO_COMPRA}"
        )
    return alerts.formatear_hodl(lista, sin_fecha, date.today())


def _record(config: Config) -> str:
    posiciones = list(_con_cambios(config).cartera)
    if not posiciones:
        return SIN_CARTERA
    filas = database.get_series(
        config.database_path,
        [p.coin_id for p in posiciones],
        record.horas(config.history_days),
        config.vs_currency,
    )
    resultado = record.calcular(cartera.serie_valor(posiciones, filas))
    if resultado is None:
        return "Aún no tengo precios guardados de tu cartera. Vuelve en un rato."
    return alerts.formatear_record(resultado, config.vs_currency)


def _rentabilidad(config: Config) -> str:
    todos = database.get_movimientos(config.database_path, None)
    if not any(m.tipo == "compra" for m in todos):
        return (
            "No has apuntado ninguna compra por aquí, y lo del PORTFOLIO del .env "
            f"no lleva fecha. Apúntalas así: {movimientos.EJEMPLO_COMPRA}"
        )
    _, tienes = rentabilidad.contables(todos)
    precios = _consultar(config, list(tienes)) if tienes else {}
    if precios is None:
        return "No he podido consultar los precios. Prueba en un rato."
    resultado = rentabilidad.calcular(todos, precios, datetime.now(timezone.utc))
    if resultado is None:
        if not rentabilidad.contables(todos)[0]:
            return (
                "Tus compras no llevan lo que costaron, así que no puedo sacar la "
                f"rentabilidad. La próxima, con precio: {movimientos.EJEMPLO_COMPRA}"
            )
        return "No he podido consultar los precios. Prueba en un rato."
    return alerts.formatear_rentabilidad(resultado, config.vs_currency)


def _calendario(config: Config, argumento: str) -> str | comandos.Foto:
    hoy = date.today()
    try:
        coin_id, año, numero = calendario.interpretar(argumento, hoy)
    except calendario.CalendarioError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {calendario.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    # Desde el día antes del 1, que hace falta para saber cómo fue el 1.
    desde = datetime(año, numero, 1).astimezone() - timedelta(days=1)
    horas = (datetime.now(timezone.utc) - desde).total_seconds() / 3600
    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    resultado = calendario.calcular(volatilidad.por_dias(serie), año, numero, hoy)
    texto = alerts.formatear_calendario(coin_id, resultado)
    if not resultado.con_dato:
        return texto
    try:
        png = grafica.dibujar_calendario(coin_id, resultado)
    except Exception as e:
        logger.warning("Mando /calendario sin imagen: %s", e)
        return texto
    return comandos.Foto(png, texto, texto)


def _compras(config: Config, argumento: str) -> str:
    coin_id = simbolos.a_id(argumento) if argumento else None
    todos = database.get_movimientos(config.database_path, None, coin_id)
    if not any(m.tipo == "compra" for m in todos):
        de = f" de <b>{telegram.escape(coin_id)}</b>" if coin_id else ""
        return (
            f"No has apuntado ninguna compra{de} por aquí. Lo del PORTFOLIO "
            f"del .env no sale. Apúntala así: {movimientos.EJEMPLO_COMPRA}"
        )
    precios = _consultar(config, list({m.coin_id for m in todos}))
    if precios is None:
        return "No he podido consultar los precios. Prueba en un rato."
    resultado = compras.calcular(todos, precios)
    if resultado is None:
        return (
            "Tus compras no llevan lo que costaron, así que no puedo saber si "
            f"fueron buenas. La próxima, con precio: {movimientos.EJEMPLO_COMPRA}"
        )
    return alerts.con_fuente(
        alerts.formatear_compras(resultado, config.vs_currency, coin_id)
    )


def _vsbtc(config: Config) -> str:
    todos = database.get_movimientos(config.database_path, None)
    if not todos:
        return (
            "No has apuntado ninguna compra por aquí, y lo del PORTFOLIO del .env "
            f"no lleva fecha. Apúntalas así: {movimientos.EJEMPLO_COMPRA}"
        )
    # Primero lo de ahora, que se guarda: así cuenta lo que apuntaste hace un rato.
    precios = _consultar(config, list({vsbtc.BITCOIN, *(m.coin_id for m in todos)}))
    if precios is None:
        return "No he podido consultar los precios. Prueba en un rato."

    primero = min(m.cuando for m in todos)
    horas = (datetime.now(timezone.utc) - primero).total_seconds() / 3600 + 24
    serie = database.get_serie(
        config.database_path, vsbtc.BITCOIN, horas, config.vs_currency
    )
    if not vsbtc.a_contar(todos, serie):
        return (
            "No tengo el precio de bitcoin de cuando apuntaste tus compras, o no "
            "llevan precio. Solo guardo el de las que vigilo: /vigilar bitcoin"
        )
    resultado = vsbtc.calcular(todos, serie, precios)
    if resultado is None:
        return "No he podido consultar los precios. Prueba en un rato."
    return alerts.con_fuente(alerts.formatear_vsbtc(resultado, config.vs_currency))


def _crear_alerta(config: Config, argumento: str) -> str:
    try:
        argumento, nota = puntuales.separar_nota(argumento)
        argumento, horas = puntuales.separar_caducidad(argumento)
    except puntuales.PuntualError as e:
        return telegram.escape(str(e))
    # Solo la cripto: le digo a cuanto esta para que sepa que poner.
    sin_objetivo = (
        len(argumento.split()) == 1 and puntuales.numero(argumento.rstrip("%")) is None
    )
    try:
        relativa = puntuales.interpretar_relativa(argumento)
        if sin_objetivo:
            coin_id = simbolos.a_id(argumento)
        elif relativa:
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

    if sin_objetivo:
        return alerts.con_fuente(
            alerts.formatear_sin_objetivo(coin_id, precio, config.vs_currency)
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

    # Con los botones 🎯 y 🔁 es facil pedir dos veces la misma, y luego llegan
    # dos avisos iguales.
    pendientes = database.get_puntuales(config.database_path, config.vs_currency)
    igual = puntuales.repetida(pendientes, coin_id, objetivo, sube)
    if igual:
        return f"Ya tienes esa alerta, es la número {igual.id}. Mira /alertas"

    alerta = database.crear_puntual(
        config.database_path,
        coin_id,
        objetivo,
        sube,
        config.vs_currency,
        puntuales.caducidad(datetime.now(timezone.utc), horas),
        nota,
    )
    logger.info("Alerta %d creada: %s a %s", alerta.id, coin_id, objetivo)
    return alerts.con_fuente(
        alerts.formatear_puntual(alerta, precio, config.vs_currency)
    )


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


def _stop(config: Config, argumento: str) -> str:
    try:
        coin_id, porcentaje = stop.interpretar(argumento)
    except stop.StopError as e:
        return telegram.escape(str(e))

    es_cartera = coin_id == puntuales.CARTERA
    posiciones = [p for p in config.cartera if es_cartera or p.coin_id == coin_id]
    if not posiciones:
        return (
            f"No tienes <b>{telegram.escape(coin_id)}</b> en la cartera. "
            "Lo que tienes, en /cartera"
        )

    try:
        precios = coingecko.get_prices(
            [p.coin_id for p in posiciones], config.vs_currency
        )
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirar el precio ahora mismo: {telegram.escape(str(e))}"
    valores, faltan = cartera.valorar(posiciones, precios)
    if faltan:
        return "Ahora mismo no tengo el precio de todo. Prueba en un rato."

    try:
        s = stop.calcular(
            coin_id, porcentaje, cartera.total(valores) if es_cartera else valores[0]
        )
    except stop.StopError as e:
        return telegram.escape(str(e))
    if s.ya_llego:
        return alerts.formatear_stop_pasado(s)

    pendientes = database.get_puntuales(config.database_path, config.vs_currency)
    igual = puntuales.repetida(pendientes, coin_id, s.objetivo, s.sube)
    if igual:
        return f"Ya lo tienes puesto, es la número {igual.id}. Mira /alertas"

    # Va como una /alerta más: así salta, se lista y se quita igual que las otras.
    alerta = database.crear_puntual(
        config.database_path,
        coin_id,
        s.objetivo,
        s.sube,
        config.vs_currency,
        None,
        s.nota,
    )
    logger.info("Stop %d creado: %s a %s", alerta.id, coin_id, s.objetivo)
    return alerts.con_fuente(alerts.formatear_stop(s, alerta.id, config.vs_currency))


def _precio(config: Config, argumento: str) -> str | comandos.ConBotones:
    comando = f"/precio {argumento}".strip()
    argumento, otra = moneda.separar(argumento)
    currency = otra or config.vs_currency
    # Lo guardado y lo que te costó la cartera van en la del .env: no se mezclan.
    otra = currency != config.vs_currency
    coin_ids = simbolos.varias(argumento)
    if not argumento:
        # A secas, las que vigilas. Si son muchas, las primeras, que no caben.
        vigiladas = _con_cambios(config).watchlist
        coin_ids = [w.coin_id for w in vigiladas][: simbolos.MAX_VARIAS]
    if not coin_ids:
        return "¿De cuál? Por ejemplo: /precio solana o /precio btc eth sol"
    if len(coin_ids) > simbolos.MAX_VARIAS:
        return f"Como mucho {simbolos.MAX_VARIAS} a la vez."

    # Con una sola, bitcoin va en la misma consulta para dar lo que vale en sats.
    pedir = coin_ids
    if len(coin_ids) == 1 and coin_ids[0] != "bitcoin":
        pedir = [*coin_ids, "bitcoin"]
    try:
        precios = coingecko.precios_semana(pedir, currency)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirar el precio ahora mismo: {telegram.escape(str(e))}"

    lineas = []
    for c in coin_ids:
        p = precios.get(c)
        if p is None:
            continue
        en_24h = p.en_24h
        if en_24h is None and not otra:
            en_24h = _variacion(config, c, p.precio)
        lineas.append((c, p.precio, en_24h, p.en_7d))
    en_1h = {c: p.en_1h for c, p in precios.items()}
    faltan = [c for c in coin_ids if c not in precios]
    if not lineas:
        return alerts.formatear_no_encuentro(faltan)

    if len(coin_ids) == 1:
        coin_id, precio, en_24h, en_7d = lineas[0]
        # Va en la moneda del .env, pero la forma de la línea es la misma.
        serie = database.get_serie(
            config.database_path, coin_id, 24, config.vs_currency
        )
        dia = [p for _, p in serie]
        bitcoin = precios.get("bitcoin")
        p = precios[coin_id]
        # leer() ya deja los dos o ninguno.
        rango_24h = (p.minimo_24h, p.maximo_24h) if p.maximo_24h else None
        emitido = (p.emitido, p.tope) if p.tope else None
        texto = alerts.con_fuente(
            alerts.formatear_precio(
                coin_id,
                precio,
                en_24h,
                currency,
                en_7d,
                en_1h.get(coin_id),
                None
                if otra
                else cartera.de(list(_con_cambios(config).cartera), coin_id, precio),
                dia,
                precios[coin_id].volumen,
                precios[coin_id].puesto,
                en_sats(coin_id, precio, bitcoin.precio if bitcoin else None),
                rango_24h,
                emitido,
                p.maximo,
                en_30d=p.en_30d,
                capitalizacion=p.capitalizacion,
            )
        )
        teclado = botones.para_precio(coin_id, grafica=len(dia) >= 2)
        return comandos.ConBotones(texto, teclado) if teclado else texto
    texto = alerts.con_fuente(alerts.formatear_precios(lineas, faltan, currency))
    # Con diez ids largos no cabe en el boton, y entonces va sin el.
    if len(comando.encode()) > botones.MAX_DATOS:
        return texto
    return comandos.ConBotones(texto, botones.actualizar(comando))


def _ath(config: Config, argumento: str) -> str:
    coin_ids = simbolos.varias(argumento)
    if not argumento:
        vigiladas = _con_cambios(config).watchlist
        coin_ids = [w.coin_id for w in vigiladas][: simbolos.MAX_VARIAS]
    if not coin_ids:
        return "¿De cuál? Por ejemplo: /ath bitcoin o /ath btc eth sol"
    if len(coin_ids) > simbolos.MAX_VARIAS:
        return f"Como mucho {simbolos.MAX_VARIAS} a la vez."

    try:
        maximos = coingecko.maximos(coin_ids, config.vs_currency)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"

    encontrados = [maximos[c] for c in coin_ids if c in maximos]
    faltan = [c for c in coin_ids if c not in maximos]
    if not encontrados:
        return alerts.formatear_no_encuentro(faltan)

    ahora = datetime.now(timezone.utc)
    if len(coin_ids) == 1:
        return alerts.con_fuente(
            alerts.formatear_maximo(encontrados[0], config.vs_currency, ahora)
        )
    return alerts.con_fuente(
        alerts.formatear_maximos(encontrados, faltan, config.vs_currency, ahora)
    )


def _tendencias(config: Config) -> str | comandos.ConBotones:
    try:
        lista = coingecko.tendencias_hoy(config.vs_currency)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"

    texto = alerts.formatear_tendencias(lista)
    if not lista:
        return texto
    return comandos.ConBotones(alerts.con_fuente(texto), botones.para_tendencias(lista))


def _top(config: Config) -> str | comandos.ConBotones:
    try:
        lista = coingecko.top_hoy(config.vs_currency)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"

    suben, bajan = top.separar(lista)
    texto = alerts.formatear_top(suben, bajan, config.vs_currency)
    if not suben and not bajan:
        return texto
    return comandos.ConBotones(alerts.con_fuente(texto), botones.actualizar("/top"))


def _ultimo(config: Config) -> str:
    vigiladas = [w.coin_id for w in _con_cambios(config).watchlist]
    if not vigiladas:
        return "No vigilas ninguna. Añade una con /vigilar"
    lista = avisados.juntar(
        vigiladas,
        database.ultimos_avisos(config.database_path),
        {c: database.get_last_price(config.database_path, c) for c in vigiladas},
    )
    return alerts.formatear_ultimo(lista, config.vs_currency)


def _aleatoria(config: Config) -> str | comandos.ConBotones:
    try:
        lista = coingecko.top_hoy(config.vs_currency)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"

    vigiladas = {w.coin_id for w in _con_cambios(config).watchlist}
    elegida = aleatoria.elegir(lista, vigiladas)
    if elegida is None:
        return "CoinGecko no me ha dado la lista ahora mismo. Prueba en un rato."
    puesto, m = elegida
    texto = alerts.formatear_aleatoria(puesto, m, config.vs_currency)
    return comandos.ConBotones(texto, botones.para_aleatoria(m.coin_id))


def _miedo() -> str | comandos.ConBotones:
    try:
        lista = miedo.pedir()
    except miedo.MiedoError as e:
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"

    texto = alerts.formatear_miedo(lista)
    if not lista:
        return texto
    return comandos.ConBotones(texto, botones.actualizar("/miedo"))


def _mercado(config: Config) -> str | comandos.ConBotones:
    try:
        datos = coingecko.mercado_global(config.vs_currency)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"

    texto = alerts.formatear_mercado(datos, config.vs_currency)
    if datos.total is None and datos.bitcoin is None:
        return texto
    return comandos.ConBotones(alerts.con_fuente(texto), botones.actualizar("/mercado"))


def _comparar(config: Config, argumento: str) -> str:
    try:
        coin_ids, horas = comparar.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not coin_ids:
        vigiladas = _con_cambios(config).watchlist
        coin_ids = [w.coin_id for w in vigiladas][: simbolos.MAX_VARIAS]
    if not coin_ids:
        return "¿Cuáles? Por ejemplo: /comparar btc eth sol 7d"

    series = {
        c: database.get_serie(config.database_path, c, horas, config.vs_currency)
        for c in coin_ids
    }
    resultados, sin_datos = comparar.comparar(series, horas, datetime.now(timezone.utc))
    if not resultados:
        return (
            f"No tengo precios guardados de ninguna ({periodo.nombre(horas)}). "
            "Solo sé de las que vigilo: míralas con /vigilar"
        )
    return alerts.con_fuente(alerts.formatear_comparar(resultados, sin_datos, horas))


def _quieta(config: Config) -> str | comandos.ConBotones:
    coin_ids = [w.coin_id for w in _con_cambios(config).watchlist]
    if not coin_ids:
        return "No vigilo ninguna. Añade alguna con /vigilar solana %5"

    series = {
        c: database.get_serie(config.database_path, c, quieta.HORAS, config.vs_currency)
        for c in coin_ids
    }
    quietas = quieta.calcular(series)
    if not quietas:
        return (
            "No tengo precios guardados de las últimas 24 h. Solo los guardo "
            "mientras estoy encendido."
        )
    texto = alerts.formatear_quieta(quietas, config.vs_currency)
    return comandos.ConBotones(texto, botones.actualizar("/quieta"))


def _volatilidad(config: Config, argumento: str) -> str:
    try:
        coin_id, horas = volatilidad.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return "¿De cuál? Por ejemplo: /volatilidad bitcoin 30d"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    resultado = volatilidad.calcular(serie)
    if resultado is None:
        return (
            f"No tengo precios guardados de <b>{telegram.escape(coin_id)}</b> de al "
            f"menos dos días ({periodo.nombre(horas)}). Solo sé de las que vigilo: "
            "míralas con /vigilar"
        )

    primero = serie[0][0]
    falta = periodo.falta_principio(primero, datetime.now(timezone.utc), horas)
    veces = {p: volatilidad.avisos(serie, p) for p in volatilidad.PRUEBAS}
    return alerts.formatear_volatilidad(
        coin_id,
        horas,
        resultado.media,
        resultado.peor,
        resultado.peor_dia,
        resultado.dias,
        veces,
        primero if falta else None,
        volatilidad.recomendar(veces, resultado.dias),
    )


def _rango(config: Config, argumento: str) -> str:
    try:
        coin_id, horas = rango.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {rango.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    # Sale de lo guardado, asi que no gasta consultas.
    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    resultado = rango.calcular(serie)
    if resultado is None:
        return (
            f"No tengo precios guardados de <b>{telegram.escape(coin_id)}</b> "
            f"({periodo.nombre(horas)}). Solo sé de las que vigilo: míralas "
            "con /vigilar"
        )

    primero = serie[0][0]
    falta = periodo.falta_principio(primero, datetime.now(timezone.utc), horas)
    return alerts.formatear_rango(
        coin_id, resultado, horas, config.vs_currency, primero if falta else None
    )


def _caida(config: Config, argumento: str) -> str:
    try:
        coin_id, horas = caida.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {caida.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    if coin_id == puntuales.CARTERA:
        config = _con_cambios(config)
        if not config.cartera:
            return SIN_CARTERA
        posiciones = list(config.cartera)
        filas = database.get_series(
            config.database_path,
            [p.coin_id for p in posiciones],
            horas,
            config.vs_currency,
        )
        serie = cartera.serie_valor(posiciones, filas)
    else:
        serie = database.get_serie(
            config.database_path, coin_id, horas, config.vs_currency
        )
    resultado = caida.calcular(serie)
    if resultado is None and coin_id == puntuales.CARTERA:
        return (
            f"Aún no tengo dos precios guardados de tu cartera "
            f"({periodo.nombre(horas)}). Vuelve a preguntar en un rato."
        )
    if resultado is None:
        return (
            f"No tengo precios guardados de <b>{telegram.escape(coin_id)}</b> "
            f"({periodo.nombre(horas)}). Solo sé de las que vigilo: míralas "
            "con /vigilar"
        )

    primero = serie[0][0]
    falta = periodo.falta_principio(primero, datetime.now(timezone.utc), horas)
    return alerts.formatear_caida(
        coin_id, resultado, horas, config.vs_currency, primero if falta else None
    )


def _sube(config: Config, argumento: str) -> str:
    try:
        coin_id, horas = sube.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {sube.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    resultado = sube.calcular(serie)
    if resultado is None:
        return (
            f"No tengo precios guardados de <b>{telegram.escape(coin_id)}</b> "
            f"({periodo.nombre(horas)}). Solo sé de las que vigilo: míralas "
            "con /vigilar"
        )

    primero = serie[0][0]
    falta = periodo.falta_principio(primero, datetime.now(timezone.utc), horas)
    return alerts.formatear_sube(
        coin_id, resultado, horas, config.vs_currency, primero if falta else None
    )


def _verdes(config: Config, argumento: str) -> str:
    try:
        coin_id, horas = verdes.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {verdes.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    resultado = verdes.calcular(volatilidad.por_dias(serie))
    if resultado is None:
        return (
            f"No tengo precios guardados de <b>{telegram.escape(coin_id)}</b> de dos "
            f"días seguidos ({periodo.nombre(horas)}). Solo sé de las que vigilo: "
            "míralas con /vigilar"
        )

    falta = periodo.falta_principio(serie[0][0], datetime.now(timezone.utc), horas)
    return alerts.formatear_verdes(coin_id, resultado, horas, falta)


def _extremo(config: Config, argumento: str) -> str:
    try:
        coin_id, horas = mejor.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {mejor.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    dias = volatilidad.por_dias(serie)
    resultado = mejor.calcular(dias)
    if resultado is None:
        return (
            f"No tengo precios guardados de <b>{telegram.escape(coin_id)}</b> de dos "
            f"días seguidos ({periodo.nombre(horas)}). Solo sé de las que vigilo: "
            "míralas con /vigilar"
        )

    falta = periodo.falta_principio(serie[0][0], datetime.now(timezone.utc), horas)
    return alerts.formatear_extremo(
        coin_id, resultado, horas, config.vs_currency, dias[0][0] if falta else None
    )


def _diasemana(config: Config, argumento: str) -> str:
    try:
        coin_id, horas = diasemana.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {diasemana.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    resultado = diasemana.calcular(volatilidad.por_dias(serie))
    if resultado is None:
        return (
            f"No tengo precios guardados de <b>{telegram.escape(coin_id)}</b> de dos "
            f"días seguidos ({periodo.nombre(horas)}). Solo sé de las que vigilo: "
            "míralas con /vigilar"
        )

    falta = periodo.falta_principio(serie[0][0], datetime.now(timezone.utc), horas)
    return alerts.formatear_diasemana(coin_id, resultado, horas, falta)


def _horas(config: Config, argumento: str) -> str:
    try:
        coin_id, tramo = horas.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {horas.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(config.database_path, coin_id, tramo, config.vs_currency)
    resultado = horas.calcular(serie)
    if resultado is None:
        return (
            f"No tengo ningún día entero de precios de <b>{telegram.escape(coin_id)}"
            f"</b> ({periodo.nombre(tramo)}). Solo sé de las que vigilo y mientras "
            "estoy encendido: míralas con /vigilar"
        )
    return alerts.formatear_horas(coin_id, resultado, tramo)


def _media(config: Config, argumento: str) -> str:
    try:
        coin_id, ventanas = media.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {media.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    # El "ahora" es el último guardado, asi no gasta consultas.
    serie = database.get_serie(
        config.database_path, coin_id, max(ventanas) * 24, config.vs_currency
    )
    dias = volatilidad.por_dias(serie)
    if not dias:
        return (
            f"No tengo precios guardados de <b>{telegram.escape(coin_id)}</b>. "
            "Solo sé de las que vigilo: míralas con /vigilar"
        )
    medias = {v: media.calcular(dias, v) for v in ventanas}
    return alerts.formatear_media(coin_id, dias[-1][1], medias, config.vs_currency)


def _racha(config: Config, argumento: str) -> str:
    if len(argumento.split()) > 1:
        return "De una en una. Por ejemplo: /racha bitcoin"
    if argumento.lower() == puntuales.CARTERA:
        return _racha_cartera(config)
    if argumento:
        coin_id = simbolos.a_id(argumento)
    else:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return "¿De cuál? Por ejemplo: /racha bitcoin"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(
        config.database_path, coin_id, racha.HORAS, config.vs_currency
    )
    dias = volatilidad.por_dias(serie)
    resultado = racha.calcular(dias)
    if resultado is None:
        return (
            f"No tengo precios guardados de <b>{telegram.escape(coin_id)}</b> de dos "
            "días seguidos que hayan cambiado. Solo sé de las que vigilo: míralas "
            "con /vigilar"
        )
    record = racha.mas_larga(dias, resultado.sube)
    return alerts.formatear_racha(
        coin_id, resultado, config.vs_currency, record, dias[0][0]
    )


def _racha_cartera(config: Config) -> str:
    posiciones = list(_con_cambios(config).cartera)
    if not posiciones:
        return SIN_CARTERA
    filas = database.get_series(
        config.database_path,
        [p.coin_id for p in posiciones],
        racha.HORAS,
        config.vs_currency,
    )
    dias = volatilidad.por_dias(cartera.serie_valor(posiciones, filas))
    resultado = racha.calcular(dias)
    if resultado is None:
        return (
            "No tengo precios guardados de tu cartera de dos días seguidos que "
            "hayan cambiado. Vuelve mañana."
        )
    record = racha.mas_larga(dias, resultado.sube)
    return alerts.formatear_racha(
        puntuales.CARTERA, resultado, config.vs_currency, record, dias[0][0]
    )


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


def _rsi(config: Config, argumento: str) -> str:
    if len(argumento.split()) > 1:
        return "De una en una. Por ejemplo: /rsi bitcoin"
    if argumento:
        coin_id = simbolos.a_id(argumento)
    else:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return "¿De cuál? Por ejemplo: /rsi bitcoin"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(
        config.database_path, coin_id, rsi.HORAS, config.vs_currency
    )
    resultado = rsi.calcular(volatilidad.por_dias(serie))
    if resultado is None:
        return (
            f"Necesito {rsi.PERIODO + 1} días seguidos de precios de "
            f"<b>{telegram.escape(coin_id)}</b> y no los tengo. Solo sé de las que "
            "vigilo, y desde que las vigilo: míralas con /vigilar"
        )
    return alerts.formatear_rsi(coin_id, resultado, config.vs_currency)


def _cuando(config: Config, argumento: str) -> str:
    try:
        coin_id, objetivo = cuando.interpretar(argumento)
    except cuando.CuandoError as e:
        return telegram.escape(str(e))

    serie = database.get_serie(
        config.database_path, coin_id, cuando.HORAS, config.vs_currency
    )
    resultado = cuando.calcular(serie, objetivo)
    if resultado is None:
        return (
            f"No tengo precios guardados de <b>{telegram.escape(coin_id)}</b>. "
            "Solo sé de las que vigilo: míralas con /vigilar"
        )
    return alerts.formatear_cuando(coin_id, resultado, config.vs_currency)


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


def _adivina(config: Config, argumento: str) -> str:
    try:
        coin_id, dicho = adivina.interpretar(argumento)
    except adivina.AdivinaError as e:
        return telegram.escape(str(e))
    precio = _precio_o_pedirlo(config, coin_id)
    if isinstance(precio, str):
        return precio
    intento = adivina.Intento(coin_id, dicho, precio)
    return alerts.formatear_adivina(intento, config.vs_currency)


def _pizza(config: Config) -> str:
    precio = _precio_o_pedirlo(config, "bitcoin")
    if isinstance(precio, str):
        return precio
    return alerts.formatear_pizza(pizza.Pizza(precio, date.today()), config.vs_currency)


def _mundo(config: Config) -> str:
    precio = _precio_o_pedirlo(config, "bitcoin")
    if isinstance(precio, str):
        return precio
    return alerts.formatear_mundo(mundo.Mundo(precio), config.vs_currency)


def _lambo(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_lambo(lambo.Lambo(valor), config.vs_currency)


def _ballena(config: Config) -> str:
    cartera = _con_cambios(config).cartera
    tienes = sum(p.cantidad for p in cartera if p.coin_id == "bitcoin")
    return alerts.formatear_ballena(ballena.Ballena(tienes))


def _cafe(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_cafe(cafe.Cafe(valor), config.vs_currency)


def _iphone(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_iphone(iphone.Iphone(valor), config.vs_currency)


def _alquiler(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_alquiler(alquiler.Alquiler(valor), config.vs_currency)


def _oro(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    onza = _precio_o_pedirlo(config, oro.COIN_ID)
    if isinstance(onza, str):
        return onza
    return alerts.formatear_oro(oro.Oro(valor, onza), config.vs_currency)


def _netflix(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_netflix(netflix.Netflix(valor), config.vs_currency)


def _ps5(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_ps5(ps5.Ps5(valor), config.vs_currency)


def _tesla(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_tesla(tesla.Tesla(valor), config.vs_currency)


def _spotify(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_spotify(spotify.Spotify(valor), config.vs_currency)


def _cana(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_cana(cana.Cana(valor), config.vs_currency)


def _switch(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_switch(switch.Switch(valor), config.vs_currency)


def _cine(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_cine(cine.Cine(valor), config.vs_currency)


def _gimnasio(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_gimnasio(gimnasio.Gimnasio(valor), config.vs_currency)


def _vuelo(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_vuelo(vuelo.Vuelo(valor), config.vs_currency)


def _super(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_super(supermercado.Super(valor), config.vs_currency)


def _kebab(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_kebab(kebab.Kebab(valor), config.vs_currency)


def _metro(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_metro(metro.Metro(valor), config.vs_currency)


def _luz(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_luz(luz.Luz(valor), config.vs_currency)


def _libro(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_libro(libro.Libro(valor), config.vs_currency)


def _concierto(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_concierto(concierto.Concierto(valor), config.vs_currency)


def _airpods(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_airpods(airpods.Airpods(valor), config.vs_currency)


def _zapatillas(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    z = zapatillas.Zapatillas(valor)
    return alerts.formatear_zapatillas(z, config.vs_currency)


def _ave(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_ave(ave.Ave(valor), config.vs_currency)


def _menu(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_menu(menu.Menu(valor), config.vs_currency)


def _hotel(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_hotel(hotel.Hotel(valor), config.vs_currency)


def _peluqueria(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    p = peluqueria.Peluqueria(valor)
    return alerts.formatear_peluqueria(p, config.vs_currency)


def _macbook(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_macbook(macbook.Macbook(valor), config.vs_currency)


def _bici(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_bici(bici.Bici(valor), config.vs_currency)


def _churros(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_churros(churros.Churros(valor), config.vs_currency)


def _loteria(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    decimos = loteria.Loteria(valor, date.today())
    return alerts.formatear_loteria(decimos, config.vs_currency)


def _piso(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_piso(piso.Piso(valor), config.vs_currency)


def _futbol(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_futbol(futbol.Futbol(valor), config.vs_currency)


def _taxi(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_taxi(taxi.Taxi(valor), config.vs_currency)


def _tortilla(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_tortilla(tortilla.Tortilla(valor), config.vs_currency)


def _videojuego(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_videojuego(videojuego.Videojuego(valor), config.vs_currency)


def _sofa(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_sofa(sofa.Sofa(valor), config.vs_currency)


def _carnet(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_carnet(carnet.Carnet(valor), config.vs_currency)


def _boda(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_boda(boda.Boda(valor), config.vs_currency)


def _jamon(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_jamon(jamon.Jamon(valor), config.vs_currency)


def _aceite(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_aceite(aceite.Aceite(valor), config.vs_currency)


def _paella(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_paella(paella.Paella(valor), config.vs_currency)


def _croquetas(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_croquetas(croquetas.Croquetas(valor), config.vs_currency)


def _pan(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_pan(pan.Pan(valor), config.vs_currency)


def _rolex(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_rolex(rolex.Rolex(valor), config.vs_currency)


def _emoji(config: Config) -> str | comandos.ConBotones:
    cambio = _cambio_cartera(config)
    if isinstance(cambio, str):
        return cambio
    return comandos.ConBotones(
        alerts.formatear_emoji(cambio), botones.actualizar("/emoji")
    )


def _tiempo(config: Config) -> str | comandos.ConBotones:
    cambio = _cambio_cartera(config)
    if isinstance(cambio, str):
        return cambio
    return comandos.ConBotones(
        alerts.formatear_tiempo(cambio), botones.actualizar("/tiempo")
    )


def _cambio_cartera(config: Config) -> float | str:
    """Lo que ha cambiado la cartera en 24 h, en %. Un str es el error."""
    config = _con_cambios(config)
    if not config.cartera:
        return SIN_CARTERA

    precios = _consultar(config, [p.coin_id for p in config.cartera])
    if precios is None:
        return "No he podido consultar los precios. Prueba en un rato."
    valores, faltan = cartera.valorar(list(config.cartera), precios)
    if faltan:
        return (
            "Ahora mismo no tengo el precio de todo lo que tienes. Prueba en un rato."
        )

    pares = []
    for v in valores:
        variacion = _variacion(config, v.coin_id, precios[v.coin_id])
        # Sin la de una, la cara sería de otra cartera: mejor no ponerla.
        if variacion is None:
            nombre = telegram.escape(v.coin_id.replace("-", " ").title())
            return f"No sé cómo iba {nombre} hace 24 h. Prueba en un rato."
        pares.append((v.valor, variacion))

    cambio = emoji.cambio(pares)
    if cambio is None:
        return "Tu cartera ahora mismo no vale nada, así que no hay nada que mirar."
    return cambio


def _coche(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_coche(coche.Coche(valor), config.vs_currency)


def _nochevieja(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    n = nochevieja.Nochevieja(valor, date.today())
    return alerts.formatear_nochevieja(n, config.vs_currency)


def _navidad(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    n = navidad.Navidad(valor, date.today())
    return alerts.formatear_navidad(n, config.vs_currency)


def _bigmac(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_bigmac(bigmac.BigMac(valor), config.vs_currency)


def _gasolina(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_gasolina(gasolina.Gasolina(valor), config.vs_currency)


def _sueldo(config: Config) -> str:
    # El SMI es en euros: con la cartera en dólares saldría una cuenta sin sentido.
    if config.vs_currency != "eur":
        return (
            "El salario mínimo va en euros. "
            "Solo funciona con <code>VS_CURRENCY=eur</code>."
        )
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_sueldo(sueldo.Sueldo(valor))


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


def _millonario(config: Config, argumento: str) -> str:
    coin_ids = simbolos.varias(argumento) or ["bitcoin"]
    if len(coin_ids) > 1:
        return "De una en una. Por ejemplo: /millonario eth"
    coin_id = coin_ids[0]
    precio = _precio_o_pedirlo(config, coin_id)
    if isinstance(precio, str):
        return precio

    tienes = next(
        (p.cantidad for p in _con_cambios(config).cartera if p.coin_id == coin_id),
        None,
    )
    unidad = simbolos.de_id(coin_id) or coin_id.replace("-", " ").title()
    return alerts.formatear_millonario(
        coin_id, unidad, millonario.Millonario(precio, tienes), config.vs_currency
    )


def _redondo(config: Config, argumento: str) -> str:
    coin_ids = simbolos.varias(argumento)
    if not argumento:
        vigiladas = _con_cambios(config).watchlist
        coin_ids = [w.coin_id for w in vigiladas][: simbolos.MAX_VARIAS]
    if not coin_ids:
        return "¿De cuál? Por ejemplo: /redondo bitcoin o /redondo btc eth"
    if len(coin_ids) > simbolos.MAX_VARIAS:
        return f"Como mucho {simbolos.MAX_VARIAS} a la vez."

    redondos = []
    for c in coin_ids:
        precio = database.get_last_price(config.database_path, c)
        if precio:
            redondos.append((c, redondo.calcular(precio)))
    if not redondos:
        nombres = ", ".join(f"<b>{telegram.escape(c)}</b>" for c in coin_ids)
        return (
            f"No tengo precios guardados de {nombres}. Solo sé de las que "
            "vigilo: míralas con /vigilar"
        )
    return alerts.formatear_redondo(redondos, config.vs_currency)


def _dia(config: Config, argumento: str) -> str:
    try:
        coin_id, fecha = dia.interpretar(argumento, date.today())
    except dia.DiaError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {dia.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(
        config.database_path, coin_id, dia.HORAS, config.vs_currency
    )
    resultado = dia.calcular(serie, fecha)
    if resultado is not None:
        return alerts.formatear_dia(coin_id, resultado, config.vs_currency)

    nombre = telegram.escape(coin_id)
    otro = dia.cercano(serie, fecha)
    if otro is None:
        return (
            f"No tengo precios guardados de <b>{nombre}</b>. Solo sé de las que "
            "vigilo: míralas con /vigilar"
        )
    return (
        f"No tengo precios de <b>{nombre}</b> del {fecha:%d/%m/%Y}. El día más "
        f"cercano que tengo es el {otro:%d/%m/%Y}: /dia {nombre} {otro:%d/%m/%Y}"
    )


def _correlacion(config: Config, argumento: str) -> str:
    try:
        ids, horas = correlacion.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not ids:
        ids = [w.coin_id for w in _con_cambios(config).watchlist[:2]]
        if len(ids) < 2:
            return f"¿Cuáles? Por ejemplo: {correlacion.EJEMPLO}"

    una, otra = (
        volatilidad.por_dias(
            database.get_serie(config.database_path, c, horas, config.vs_currency)
        )
        for c in ids
    )
    resultado = correlacion.calcular(una, otra)
    if resultado is None:
        nombres = " y ".join(f"<b>{telegram.escape(c)}</b>" for c in ids)
        return (
            f"Necesito al menos {correlacion.MINIMO} días seguidos con precios de "
            f"{nombres} ({periodo.nombre(horas)}) y no los tengo. Solo sé de las "
            "que vigilo: míralas con /vigilar"
        )
    return alerts.formatear_correlacion(*ids, resultado, horas)


def _hoy(config: Config, argumento: str) -> str | comandos.ConBotones:
    coin_ids = simbolos.varias(argumento)
    if not argumento:
        coin_ids = [w.coin_id for w in _con_cambios(config).watchlist]
    if not coin_ids:
        return "¿De cuáles? Por ejemplo: /hoy o /hoy btc eth"
    if len(coin_ids) > simbolos.MAX_VARIAS:
        return f"Como mucho {simbolos.MAX_VARIAS} a la vez."

    ahora = datetime.now(timezone.utc)
    desde = hoy.medianoche(ahora)
    # Una hora antes de las 00:00, para tener el último precio de ayer.
    horas_atras = (ahora - desde).total_seconds() / 3600 + 1
    lineas = []
    ultimo = None
    for c in coin_ids:
        serie = database.get_serie(
            config.database_path, c, horas_atras, config.vs_currency
        )
        lineas.append((c, hoy.calcular(serie, desde)))
        if serie and (ultimo is None or serie[-1][0] > ultimo):
            ultimo = serie[-1][0]

    if all(h is None for _, h in lineas):
        return (
            "No tengo precios guardados de hoy. Solo sé de las que vigilo, y "
            "mientras estoy encendido: míralas con /vigilar"
        )
    texto = alerts.formatear_hoy(lineas, config.vs_currency, ultimo)
    comando = f"/hoy {argumento}".strip()
    # Con muchas criptos escritas no cabe en el botón: va sin él.
    if len(comando.encode()) > botones.MAX_DATOS:
        return texto
    return comandos.ConBotones(texto, botones.actualizar(comando))


def _ratio(config: Config, argumento: str) -> str:
    try:
        ids, horas = ratio.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not ids:
        ids = [w.coin_id for w in _con_cambios(config).watchlist[:2]]
        if len(ids) < 2:
            return f"¿Cuáles? Por ejemplo: {ratio.EJEMPLO}"

    una, otra = (
        volatilidad.por_dias(
            database.get_serie(config.database_path, c, horas, config.vs_currency)
        )
        for c in ids
    )
    resultado = ratio.calcular(una, otra)
    if resultado is None:
        nombres = " y ".join(f"<b>{telegram.escape(c)}</b>" for c in ids)
        return (
            f"Necesito precios de {nombres} de al menos dos días "
            f"({periodo.nombre(horas)}) y no los tengo. Solo sé de las que vigilo: "
            "míralas con /vigilar"
        )
    return alerts.formatear_ratio(*ids, resultado, horas)


def _convertir(config: Config, argumento: str) -> str:
    try:
        conversion = convertir.interpretar(argumento, config.vs_currency)
    except convertir.ConvertirError as e:
        return telegram.escape(str(e))

    coin_id = conversion.coin_id
    # Las dos en la misma consulta, que gasta lo mismo que una.
    pedidas = [coin_id, conversion.hacia] if conversion.hacia else [coin_id]
    try:
        precios = coingecko.get_prices(pedidas, config.vs_currency)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirar el precio ahora mismo: {telegram.escape(str(e))}"
    for pedida in pedidas:
        if not precios.get(pedida):
            return (
                f"No encuentro <b>{telegram.escape(pedida)}</b> en CoinGecko. "
                f"Prueba con /buscar {telegram.escape(pedida)}"
            )

    precio = precios[coin_id]
    if conversion.hacia:
        precio_hacia = precios[conversion.hacia]
        return alerts.con_fuente(
            alerts.formatear_cambio(
                conversion.cantidad,
                coin_id,
                conversion.entre(precio, precio_hacia),
                conversion.hacia,
                (precio, precio_hacia),
                config.vs_currency,
                conversion.sats,
                conversion.hacia_sats,
            )
        )

    resultado = conversion.resultado(precio)
    dinero, cripto = (
        (conversion.cantidad, resultado)
        if conversion.desde_dinero
        else (resultado, conversion.cantidad)
    )
    return alerts.con_fuente(
        alerts.formatear_conversion(
            dinero,
            cripto,
            coin_id,
            precio,
            conversion.desde_dinero,
            config.vs_currency,
            conversion.sats,
            _variacion(config, coin_id, precio),
        )
    )


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


def _si(config: Config, argumento: str) -> str:
    try:
        pregunta = hubiera.interpretar(argumento, config.vs_currency)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))

    coin_id, horas = pregunta.coin_id, pregunta.horas
    # Con lo guardado y no con el precio de CoinGecko: asi no gasta consultas.
    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    if len(serie) < 2:
        nombre = telegram.escape(coin_id)
        return (
            f"No tengo precios guardados de <b>{nombre}</b> ({periodo.nombre(horas)}). "
            f"Solo sé de las que vigilo: míralas con /vigilar"
        )

    primero, ultimo = serie[0][0], serie[-1][0]
    ahora = datetime.now(timezone.utc)
    falta = periodo.falta_principio(primero, ahora, horas)
    # Con el bot parado unos dias, el "ahora" seria un precio viejo.
    viejo = ahora - ultimo > timedelta(hours=1)
    return alerts.con_fuente(
        alerts.formatear_hubiera(
            pregunta.cantidad,
            coin_id,
            serie[0][1],
            serie[-1][1],
            horas,
            primero if falta else None,
            config.vs_currency,
            ultimo if viejo else None,
        )
    )


def _dca(config: Config, argumento: str) -> str:
    try:
        plan = dca.interpretar(argumento, config.vs_currency)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))

    coin_id, horas = plan.coin_id, plan.horas
    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    resultado = dca.calcular(serie, plan.cantidad, plan.cada) if serie else None
    if len(serie) < 2 or not resultado.compras:
        nombre = telegram.escape(coin_id)
        return (
            f"No tengo precios guardados de <b>{nombre}</b> ({periodo.nombre(horas)}). "
            f"Solo sé de las que vigilo: míralas con /vigilar"
        )

    primero, ultimo = serie[0][0], serie[-1][0]
    ahora = datetime.now(timezone.utc)
    falta = periodo.falta_principio(primero, ahora, horas)
    viejo = ahora - ultimo > timedelta(hours=1)
    return alerts.con_fuente(
        alerts.formatear_dca(
            plan.cantidad,
            coin_id,
            dca.TEXTO[plan.frecuencia],
            resultado.compras,
            resultado.cripto,
            resultado.valor,
            horas,
            primero if falta else None,
            config.vs_currency,
            ultimo if viejo else None,
            resultado.de_golpe,
        )
    )


def _equilibrio(config: Config) -> str | comandos.ConBotones:
    config = _con_cambios(config)
    if not config.cartera:
        return SIN_CARTERA

    precios = _consultar(config, [p.coin_id for p in config.cartera])
    if precios is None:
        return "No he podido consultar los precios. Prueba en un rato."
    valores, faltan = cartera.valorar(list(config.cartera), precios)
    # Sin el precio de alguna, el total saldría más bajo de lo que es.
    if faltan:
        return (
            "Ahora mismo no tengo el precio de todo lo que tienes. Prueba en un rato."
        )
    resultado = equilibrio.calcular(valores)
    if not resultado.criptos:
        return (
            "No sé lo que te costó nada de la cartera. Apúntalo al comprar: "
            "/compra bitcoin 0.01 600"
        )
    texto = alerts.con_fuente(
        alerts.formatear_equilibrio(resultado, config.vs_currency)
    )
    return comandos.ConBotones(texto, botones.actualizar("/equilibrio"))


def _doble(config: Config) -> str | comandos.ConBotones:
    config = _con_cambios(config)
    if not config.cartera:
        return SIN_CARTERA

    precios = _consultar(config, [p.coin_id for p in config.cartera])
    if precios is None:
        return "No he podido consultar los precios. Prueba en un rato."
    valores, faltan = cartera.valorar(list(config.cartera), precios)
    if faltan:
        return (
            "Ahora mismo no tengo el precio de todo lo que tienes. Prueba en un rato."
        )
    resultado = doble.calcular(valores)
    if not resultado.criptos:
        return (
            "No sé lo que te costó nada de la cartera. Apúntalo al comprar: "
            "/compra bitcoin 0.01 600"
        )
    texto = alerts.con_fuente(alerts.formatear_doble(resultado, config.vs_currency))
    return comandos.ConBotones(texto, botones.actualizar("/doble"))


def _mitad(config: Config) -> str | comandos.ConBotones:
    config = _con_cambios(config)
    if not config.cartera:
        return SIN_CARTERA

    precios = _consultar(config, [p.coin_id for p in config.cartera])
    if precios is None:
        return "No he podido consultar los precios. Prueba en un rato."
    valores, faltan = cartera.valorar(list(config.cartera), precios)
    if faltan:
        return (
            "Ahora mismo no tengo el precio de todo lo que tienes. Prueba en un rato."
        )
    resultado = mitad.calcular(valores)
    if not resultado.criptos:
        return (
            "No sé lo que te costó nada de la cartera. Apúntalo al comprar: "
            "/compra bitcoin 0.01 600"
        )
    texto = alerts.con_fuente(alerts.formatear_mitad(resultado, config.vs_currency))
    return comandos.ConBotones(texto, botones.actualizar("/mitad"))


def _meta(config: Config, argumento: str) -> str:
    try:
        cifra = meta.interpretar(argumento)
    except meta.MetaError as e:
        return telegram.escape(str(e))
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    if valor <= 0:
        return "Tu cartera ahora mismo vale 0, así que no hay por dónde empezar."
    return alerts.formatear_meta(meta.Meta(valor, cifra), config.vs_currency)


def _objetivo(config: Config, argumento: str) -> str:
    config = _con_cambios(config)
    if not config.cartera:
        return SIN_CARTERA
    try:
        coin_id, precio = objetivo.interpretar(argumento)
    except objetivo.ObjetivoError as e:
        return telegram.escape(str(e))
    # Antes de gastar una consulta, que si no la tienes no hay nada que calcular.
    if coin_id not in {p.coin_id for p in config.cartera}:
        return (
            f"No tienes <b>{telegram.escape(coin_id)}</b> en la cartera. "
            "Mira lo que tienes con /cartera"
        )

    precios = _consultar(config, [p.coin_id for p in config.cartera])
    if precios is None:
        return "No he podido consultar los precios. Prueba en un rato."
    valores, faltan = cartera.valorar(list(config.cartera), precios)
    escenario = objetivo.calcular(valores, coin_id, precio)
    # Sin el precio de alguna, el total saldria mas bajo de lo que es.
    if faltan or escenario is None:
        return (
            "Ahora mismo no tengo el precio de todo lo que tienes. Prueba en un rato."
        )
    return alerts.con_fuente(alerts.formatear_objetivo(escenario, config.vs_currency))


def _promediar(config: Config, argumento: str) -> str:
    config = _con_cambios(config)
    if not config.cartera:
        return SIN_CARTERA
    try:
        coin_id, precio = promediar.interpretar(argumento)
    except promediar.PromediarError as e:
        return telegram.escape(str(e))
    if coin_id not in {p.coin_id for p in config.cartera}:
        return (
            f"No tienes <b>{telegram.escape(coin_id)}</b> en la cartera. "
            "Mira lo que tienes con /cartera"
        )

    precios = _consultar(config, [coin_id])
    if not precios or coin_id not in precios:
        return "No he podido consultar los precios. Prueba en un rato."
    valor = cartera.de(list(config.cartera), coin_id, precios[coin_id])
    promedio = promediar.calcular(valor, precio)
    if promedio is None:
        return (
            f"No sé lo que te costó <b>{telegram.escape(coin_id)}</b>. "
            "Apúntalo al comprar: /compra bitcoin 0.01 600"
        )
    return alerts.con_fuente(alerts.formatear_promediar(promedio, config.vs_currency))


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


TITULO_DIARIO = "☀️ <b>Tu resumen del día</b>"


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


def _mes(config: Config) -> str | comandos.Foto:
    ahora = datetime.now(timezone.utc)
    nombre = mes.nombre(ahora)
    return _desde_el_principio(
        config, mes.horas(ahora), f"Tu {nombre}", "mes", f"Desde el 1 de {nombre}"
    )


def _anual(config: Config, argumento: str = "") -> str | comandos.Foto:
    ahora = datetime.now(timezone.utc)
    if argumento:
        try:
            año = anual.interpretar(argumento, date.today().year)
        except anual.AnualError as e:
            return telegram.escape(str(e))
        config = _con_cambios(config)
        return alerts.formatear_anual(
            _leer_año(config, año), config.vs_currency, date.today()
        )
    return _desde_el_principio(
        config,
        mes.horas_del_ano(ahora),
        f"Tu {ahora.astimezone().year}",
        "año",
        "Desde el 1 de enero",
    )


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
        minutos = minutos_mute(duracion, datetime.now().astimezone())
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


def _cartera(
    config: Config, argumento: str
) -> str | comandos.Foto | comandos.ConBotones:
    """/cartera con la grafica de lo que ha valido. Sin datos, solo el texto."""
    resto, otra = moneda.separar(argumento)
    if otra and otra != config.vs_currency:
        return _cartera_en(config, otra, f"/cartera {argumento}")
    argumento = resto
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


def _cartera_en(
    config: Config, currency: str, comando: str
) -> str | comandos.ConBotones:
    """/cartera usd: lo que vale en otra moneda, sin ganancias ni grafica."""
    try:
        precios = coingecko.get_prices([p.coin_id for p in config.cartera], currency)
    except coingecko.CoinGeckoError as e:
        logger.error("No se pudieron consultar los precios: %s", e)
        precios = {}
    if not precios:
        return "No he podido consultar los precios. Prueba en un rato."

    # Lo que te costo esta en la moneda del .env: pasarlo al cambio de hoy mentiria.
    sin_coste = [replace(p, invertido=None) for p in config.cartera]
    valores, faltan = cartera.valorar(sin_coste, precios)
    texto = alerts.formatear_cartera(valores, cartera.total(valores), faltan, currency)
    texto += (
        f"\n<i>Lo que ganas o pierdes solo te lo sé decir en "
        f"{config.vs_currency.upper()}, que es en lo que apuntaste lo que te costó.</i>"
    )
    return comandos.ConBotones(alerts.con_fuente(texto), botones.actualizar(comando))


def _reparto(config: Config) -> str | comandos.Foto:
    precios = _consultar(config, [p.coin_id for p in config.cartera])
    if precios is None:
        return "No he podido consultar los precios. Prueba en un rato."
    valores, faltan = cartera.valorar(list(config.cartera), precios)
    # Sin una, los % de las demás saldrían inflados.
    if faltan:
        return (
            "No tengo el precio de "
            + ", ".join(f"<b>{telegram.escape(c)}</b>" for c in faltan)
            + " y sin ella el reparto saldría mal. Prueba en un rato."
        )

    trozos = reparto.trozos(valores)
    total = cartera.total(valores).valor
    if not trozos:
        return "Tu cartera ahora mismo no vale nada, no hay nada que repartir."
    texto = alerts.con_fuente(
        alerts.formatear_reparto(trozos, total, config.vs_currency)
    )
    try:
        png = grafica.dibujar_reparto(trozos, total, config.vs_currency)
    except Exception as e:
        logger.warning("Mando /reparto sin imagen: %s", e)
        return texto
    return comandos.Foto(png, texto, texto)


def _riesgo(config: Config) -> str:
    posiciones = list(config.cartera)
    coin_ids = [p.coin_id for p in posiciones]
    precios = _consultar(config, coin_ids)
    if precios is None:
        return "No he podido consultar los precios. Prueba en un rato."
    valores, faltan = cartera.valorar(posiciones, precios)
    if faltan:
        return (
            "No tengo el precio de "
            + ", ".join(f"<b>{telegram.escape(c)}</b>" for c in faltan)
            + " y sin ella las cuentas saldrían mal. Prueba en un rato."
        )

    filas = database.get_series(
        config.database_path, coin_ids, riesgo.HORAS, config.vs_currency
    )
    movimiento = volatilidad.calcular(cartera.serie_valor(posiciones, filas))
    # Para comparar; si no vigilas bitcoin, sale sin esa línea.
    btc = volatilidad.calcular(
        database.get_serie(
            config.database_path, "bitcoin", riesgo.HORAS, config.vs_currency
        )
    )
    resultado = riesgo.calcular(valores, movimiento, btc.media if btc else None)
    if resultado is None:
        return "Tu cartera ahora mismo no vale nada, no hay riesgo que medir."
    return alerts.con_fuente(alerts.formatear_riesgo(resultado, config.vs_currency))


def _rebalanceo(config: Config, argumento: str) -> str:
    try:
        reparto = rebalanceo.interpretar(argumento)
    except rebalanceo.RebalanceoError as e:
        return telegram.escape(str(e))
    iguales = reparto is None
    if reparto is None:
        reparto = rebalanceo.iguales([p.coin_id for p in config.cartera])

    tienes = [p.coin_id for p in config.cartera]
    precios = _consultar(config, list(dict.fromkeys([*tienes, *reparto])))
    if precios is None:
        return "No he podido consultar los precios. Prueba en un rato."
    # Una que no tienes y no sale suele ser un nombre mal escrito.
    nuevas = [c for c in reparto if c not in tienes and c not in precios]
    if nuevas:
        return (
            "No encuentro "
            + ", ".join(f"<b>{telegram.escape(c)}</b>" for c in nuevas)
            + ". Ponla con su símbolo (btc) o su id de CoinGecko (bitcoin)."
        )
    valores, faltan = cartera.valorar(list(config.cartera), precios)
    if faltan:
        return (
            "No tengo el precio de "
            + ", ".join(f"<b>{telegram.escape(c)}</b>" for c in faltan)
            + " y sin ella las cuentas saldrían mal. Prueba en un rato."
        )

    pasos = rebalanceo.calcular(valores, reparto, precios)
    if not pasos:
        return "Tu cartera ahora mismo no vale nada, no hay nada que repartir."
    total = cartera.total(valores).valor
    return alerts.con_fuente(
        alerts.formatear_rebalanceo(pasos, total, config.vs_currency, iguales)
    )


def montar_cartera(config: Config) -> str | None:
    """Solo la cartera, sin el resto del resumen. None si no hay precios."""
    coin_ids = [p.coin_id for p in config.cartera]
    # Bitcoin va en la misma consulta para dar el total en sats.
    pedir = coin_ids if "bitcoin" in coin_ids else [*coin_ids, "bitcoin"]
    precios = _consultar(config, pedir)
    if precios is None:
        return None
    return alerts.con_fuente(_bloque_cartera(config, precios, con_sats=True))


def _bloque_cartera(
    config: Config, precios: dict[str, float], con_sats: bool = False
) -> str:
    valores, faltan = cartera.valorar(list(config.cartera), precios)
    suma = cartera.total(valores)
    sats = None
    bitcoin = precios.get("bitcoin")
    # Con solo bitcoin seria repetir lo que tienes, que ya se ve arriba.
    if con_sats and bitcoin and any(v.coin_id != "bitcoin" for v in valores):
        sats = suma.valor / bitcoin * alerts.POR_BTC
    return alerts.formatear_cartera(valores, suma, faltan, config.vs_currency, sats)


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
        help="calla los avisos un rato (30m, 2h, 1d, 'hasta 8:00') y sale",
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
