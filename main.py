"""Punto de entrada: consulta precios, los guarda, compara y avisa.

Uso:
    python main.py                    una consulta y sale
    python main.py --loop             vigila en bucle
    python main.py --test             manda un mensaje de prueba a Telegram
    python main.py --status           manda un resumen de como van los precios
    python main.py --mute 2h          calla los avisos durante dos horas
    python main.py --unmute           vuelve a avisar
    python main.py --history bitcoin  muestra el historico guardado
    python main.py --panel            abre el panel web en el navegador
"""

import argparse
import logging
import sys
import time
from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

from crypto_tracker import (
    adios,
    adivina,
    ajustes,
    alertaratio,
    alerts,
    backup,
    binance,
    bola,
    botones,
    brusco,
    buzon,
    cada,
    calendario,
    callar,
    caraocruz,
    cartera,
    chiste,
    coingecko,
    comandos,
    comparar,
    condicion,
    consejo,
    contexto,
    copia,
    cumple,
    cuota,
    dado,
    database,
    dato,
    dca,
    diario,
    emocion,
    estacional,
    ethereum,
    excusa,
    exportar,
    extremos,
    fantasma,
    frase,
    funding,
    galleta,
    grafica,
    halving,
    herencia,
    horoscopo,
    hubiera,
    importar,
    maximo,
    merge,
    miedo,
    movimientos,
    panel,
    panel_html,
    perdido,
    periodo,
    ppt,
    puntuales,
    quieta,
    quiz,
    refran,
    rellenar,
    ruido,
    salud,
    sesgo,
    simbolos,
    stop,
    tarot,
    telegram,
    version,
    volatilidad,
    whitepaper,
)
from crypto_tracker.config import (
    Config,
    ConfigError,
    load_config,
    minutos_mute,
)
from crypto_tracker.respuestas import comparaciones
from crypto_tracker.respuestas.alertas import (
    _alertas,
    _comando_quitar,
    _comando_vigilar,
    _crear_alerta,
    _dejar,
    _escalera,
    _rezagada,
    _stop,
)
from crypto_tracker.respuestas.analisis import (
    _backtest,
    _bollinger,
    _caida,
    _correlacion,
    _cuando,
    _diames,
    _diasemana,
    _estocastico,
    _extremo,
    _fibonacci,
    _futuro,
    _horas,
    _macd,
    _media,
    _racha,
    _rango,
    _ratio,
    _rsi,
    _sharpe,
    _soporte,
    _sube,
    _verdes,
)
from crypto_tracker.respuestas.base import (
    SIN_CARTERA,
    Respuesta,
    _alertas_ratio,
    _con_cambios,
    _consultar,
    _indicador,
    _precio_o_pedirlo,
    _puntuales,
    _silenciado,
    _sin_sonido,
    _variacion,
)
from crypto_tracker.respuestas.cartera import (
    _apodo,
    _apy,
    _arrepentido,
    _cartera,
    _comisiones,
    _compensar,
    _comprar,
    _compras,
    _corregir,
    _deposito,
    _deshacer,
    _doble,
    _equilibrio,
    _ganancias,
    _hodl,
    _impuestos,
    _inflacion,
    _limite,
    _meta,
    _mitad,
    _modelo721,
    _movimientos,
    _objetivo,
    _pelotazo,
    _permuta,
    _plan,
    _posicion,
    _primera,
    _promediar,
    _rebalanceo,
    _recompensa,
    _record,
    _rentabilidad,
    _reparto,
    _riesgo,
    _sivendo,
    _tarjeta,
    _timing,
    _vender,
    _vsbolsa,
    _vsbtc,
)
from crypto_tracker.respuestas.mercado import (
    _aleatoria,
    _ath,
    _comisionred,
    _convertir,
    _dia,
    _direccion,
    _dominancia,
    _funding,
    _hoy,
    _mercado,
    _miedo,
    _precio,
    _redondo,
    _tendencias,
    _top,
    _ultimo,
    foto_dominancia,
)
from crypto_tracker.respuestas.recordatorios import (
    _pienso,
    _prediccion,
    _recordar,
    cerrar_predicciones,
    pensados,
    recordatorios,
)
from crypto_tracker.respuestas.resumenes import (
    _anual,
    _comando_resumen,
    _comando_status,
    _mes,
    _semana,
    aviso_compensar,
    copia_semanal,
    enviar_resumen,
    resumen_anual,
    resumen_diario,
    resumen_mensual,
    resumen_semanal,
)
from crypto_tracker.respuestas.revisiones import (
    _calma_de,
    _mandar_sueltos,
    revisar_721,
    revisar_alertas_ratio,
    revisar_bajon,
    revisar_calma,
    revisar_concentracion,
    revisar_cruces,
    revisar_direcciones,
    revisar_equilibrio,
    revisar_estables,
    revisar_rezagadas,
    revisar_rsi,
    revisar_volumen,
)

logger = logging.getLogger("crypto_tracker")

# Si el ciclo falla estas veces seguidas, algo va mal de verdad y paramos.
MAX_FALLOS = 10


# Segundos que Telegram aguanta la conexion abierta esperando un mensaje.
ESPERA_TELEGRAM = 30

# Lo que escribiste con el bot apagado no se contesta: un /mute de anoche
# no pinta nada esta mañana.
ANTIGUEDAD_MAXIMA = 10 * 60

# El del bucle en marcha, para que /bot sepa como va. None fuera de --loop.
_pulso: salud.Pulso | None = None
# Lo leído del último CSV, a la espera de que pulses Importar. Si se reinicia
# el bot se pierde, pero basta con volver a mandarlo.
_importacion: list[importar.Operacion] | None = None
# Un historial de años de Binance no llega ni a 1 MB.
MAX_CSV = 5 * 1024 * 1024


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
    extra += alertaratio.criptos(_alertas_ratio(config))
    extra = [c for c in extra if c not in coin_ids and c != puntuales.CARTERA]

    todas = coin_ids + list(dict.fromkeys(extra))
    respaldo = False
    try:
        precios = coingecko.get_prices(todas, config.vs_currency)
    except coingecko.CoinGeckoError as e:
        logger.error("No se pudieron consultar los precios: %s", e)
        precios = _precios_de_binance(todas, config.vs_currency)
        if not precios:
            return estado, str(e)
        respaldo = True

    # Con los de Binance faltarán las que no tiene, pero CoinGecko sí las conoce.
    if not respaldo:
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
        database.save_prices(
            config.database_path,
            precios,
            config.vs_currency,
            coingecko.volumenes(list(precios)),
        )
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

    pendientes = subir_moviles(config, pendientes, con_cartera)
    pendientes = seguir_stops(config, pendientes)
    hechas = puntuales.cumplidas(pendientes, con_cartera)
    hechas, lecturas = _con_condicion(config, hechas)
    avisos += [
        alerts.Alert(
            p.coin_id,
            con_cartera[p.coin_id],
            p.objetivo,
            alerts.ALTO if p.sube else alerts.BAJO,
            puntual=True,
            nota=p.nota,
            condicion=lecturas.get(p.id),
        )
        for p in hechas
    ]

    if not respaldo and avisos:
        raras = _sospechosas(
            config,
            {a.coin_id: precios.get(a.coin_id) for a in avisos},
            antes_de_guardar,
        )
        if raras:
            avisos = [a for a in avisos if a.coin_id not in raras]
            hechas = [p for p in hechas if p.coin_id not in raras]
            # Como si no hubiera pasado: el siguiente ciclo lo vuelve a mirar.
            estado_nuevo = dict(estado_nuevo)
            for c in raras:
                if c in estado:
                    estado_nuevo[c] = estado[c]
                else:
                    estado_nuevo.pop(c, None)

    # Guardamos la zona de cada cripto para no repetir el aviso al reiniciar.
    try:
        database.save_state(config.database_path, estado_nuevo)
    except database.DatabaseError as e:
        logger.error("No se pudo guardar el estado de las alertas: %s", e)

    # Como con el /mute de todas: las de /alerta no se borran y saltan al volver.
    calladas = _calladas(config)
    # Si saltan cinco a la vez, mejor un mensaje que cinco notificaciones.
    sueltos = buzon.Buzon()
    revisar_bajon(config, valor, calladas, sueltos)
    revisar_concentracion(config, precios, calladas, sueltos)
    revisar_equilibrio(config, precios, calladas, sueltos)
    revisar_rezagadas(config, precios, sueltos)
    revisar_alertas_ratio(config, precios, calladas, sueltos)
    revisar_rsi(config, vigiladas, calladas, sueltos)
    revisar_cruces(config, vigiladas, calladas, sueltos)
    revisar_estables(config, list(precios), calladas, sueltos)
    revisar_volumen(config, vigiladas, calladas, sueltos)
    revisar_calma(config, vigiladas, calladas, sueltos)
    revisar_721(config, valor, calladas, sueltos)
    revisar_direcciones(config, precios.get("bitcoin"), sueltos)
    if calladas:
        avisos = [a for a in avisos if a.coin_id not in calladas]
        hechas = [p for p in hechas if p.coin_id not in calladas]

    if not avisos:
        logger.info("Ningun umbral cruzado")
        _mandar_sueltos(config, sueltos)
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
        _mandar_sueltos(config, sueltos)
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
    avisos = [replace(a, contexto=_contexto(config, a)) for a in avisos]

    # Todo en un mensaje: si cruzan tres a la vez, tres notificaciones
    # seguidas molestan y encima Telegram empieza a cortar el ritmo.
    texto = alerts.formatear_varios(avisos, config.vs_currency)
    quitadas = _de_pareja(config, pendientes, hechas)
    if quitadas:
        texto += "\n\n" + alerts.formatear_pareja_quitada(quitadas, config.vs_currency)
    if not sueltos.vacio():
        texto += "\n\n" + "\n\n".join(sueltos.textos)
    if respaldo:
        texto = f"{texto}\n\n{binance.FUENTE}"
    else:
        texto = alerts.con_fuente(texto)
    cruzadas = ", ".join(f"{a.coin_id} {a.estado}" for a in avisos)

    if telegram.send_message(
        config.telegram_token,
        config.telegram_chat_id,
        texto,
        sin_sonido=_sin_sonido(config),
        botones=botones.para_avisos(avisos, config.vs_currency),
    ):
        logger.info("Aviso enviado (%d): %s", len(avisos), cruzadas)
        _borrar_puntuales(config, hechas + quitadas)
        _apuntar_avisos(config, avisos)
        sueltos.llegaron()
    else:
        # Ni con los reintentos ha salido y el estado ya cambio. El siguiente
        # cruce volvera a avisar; las de /alerta siguen ahi.
        logger.error("No se pudo avisar de: %s", cruzadas)

    return estado_nuevo, None


def _con_condicion(
    config: Config, hechas: list[puntuales.Puntual]
) -> tuple[list[puntuales.Puntual], dict[int, tuple[condicion.Condicion, float]]]:
    """De las que han llegado al precio, las que además cumplen lo del miedo o RSI.

    Las otras se quedan esperando: si luego cambia el miedo, saltan entonces.
    """
    valores: dict[tuple[str, str], float | None] = {}
    listas, lecturas = [], {}
    for p in hechas:
        c = p.condicion
        if c is None:
            listas.append(p)
            continue
        # El miedo es el mismo para todas; una sola consulta por ciclo.
        clave = (c.indicador, "" if c.indicador == "miedo" else p.coin_id)
        if clave not in valores:
            valores[clave] = _indicador(config, c.indicador, p.coin_id)
        actual = valores[clave]
        if actual is not None and c.cumple(actual):
            listas.append(p)
            lecturas[p.id] = (c, actual)
    return listas, lecturas


def _contexto(config: Config, aviso: alerts.Alert) -> contexto.Contexto | None:
    if aviso.coin_id == puntuales.CARTERA or aviso.variacion_24h is None:
        return None
    try:
        serie = database.get_serie(
            config.database_path, aviso.coin_id, contexto.HORAS, config.vs_currency
        )
    except database.DatabaseError as e:
        # Es un extra; el aviso sale igual sin esa línea.
        logger.warning("Aviso sin contexto de %s: %s", aviso.coin_id, e)
        return None
    return contexto.buscar(serie, aviso.variacion_24h)


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


def _de_pareja(
    config: Config,
    pendientes: list[puntuales.Puntual],
    hechas: list[puntuales.Puntual],
) -> list[puntuales.Puntual]:
    """Las que sobran porque ha saltado su pareja."""
    if not hechas:
        return []
    try:
        parejas = database.parejas(config.database_path)
    except database.DatabaseError as e:
        # Se queda la otra puesta; te llegaría luego, pero no se pierde nada.
        logger.error("No se pudieron leer las parejas de /alerta: %s", e)
        return []
    otras = puntuales.otras_de_pareja([h.id for h in hechas], parejas)
    return [p for p in pendientes if p.id in otras]


def _borrar_puntuales(config: Config, hechas: list[puntuales.Puntual]) -> None:
    for p in hechas:
        try:
            database.borrar_puntual(config.database_path, p.id)
        except database.DatabaseError as e:
            # Volvera a avisar el siguiente ciclo. Mejor repetido que perdido.
            logger.error("No se pudo borrar la alerta %d: %s", p.id, e)


def _precios_de_binance(coin_ids: list[str], vs_currency: str) -> dict[str, float]:
    """El plan B cuando CoinGecko no contesta, para no quedarse sin avisos."""
    try:
        precios = binance.precios(coin_ids, vs_currency)
    except binance.BinanceError as e:
        logger.error("%s", e)
        return {}
    if precios:
        # Lo de la última consulta buena ya es viejo; sin él se mira el histórico.
        coingecko.olvidar_24h()
        logger.warning("Tiro de los precios de Binance para: %s", ", ".join(precios))
    return precios


def _sospechosas(
    config: Config, precios: dict[str, float | None], guardado: datetime
) -> set[str]:
    """Las que van a avisar con un precio que Binance no ve ni de cerca."""
    # La cartera no está en Binance, y sin precio no hay nada que comparar.
    precios = {c: p for c, p in precios.items() if p and c != puntuales.CARTERA}
    try:
        otros = binance.precios(list(precios), config.vs_currency)
        antes = {
            c: database.precio_antes(config.database_path, c, guardado) for c in otros
        }
    except (binance.BinanceError, database.DatabaseError) as e:
        # Sin con qué comparar, avisamos igual: mejor eso que callar uno bueno.
        logger.warning("No he podido comparar con Binance: %s", e)
        return set()
    raras = binance.sospechosas(precios, antes, otros)
    for c in raras:
        logger.warning(
            "No aviso de %s: CoinGecko dice %s y Binance %s", c, precios[c], otros[c]
        )
    return set(raras)


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


def subir_moviles(
    config: Config, pendientes: list[puntuales.Puntual], precios: dict[str, float]
) -> list[puntuales.Puntual]:
    """Los /stop movil suben con el precio. Bajando se quedan donde estaban."""
    try:
        moviles = database.moviles(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer los stops móviles: %s", e)
        return pendientes

    salen = []
    for a in pendientes:
        precio = precios.get(a.coin_id)
        nuevo = None
        if a.id in moviles and precio is not None:
            nuevo = stop.subir(a.objetivo, moviles[a.id], precio)
        if nuevo is None:
            salen.append(a)
            continue
        try:
            database.subir_puntual(config.database_path, a.id, nuevo)
        except database.DatabaseError as e:
            logger.error("No se pudo subir el stop móvil %d: %s", a.id, e)
            salen.append(a)
            continue
        logger.info("Stop móvil %d sube a %s", a.id, nuevo)
        salen.append(replace(a, objetivo=nuevo))
    return salen


def seguir_stops(
    config: Config, pendientes: list[puntuales.Puntual]
) -> list[puntuales.Puntual]:
    """Los /stop van sobre tu precio medio: si compras o vendes, se mueven con él."""
    try:
        porcentajes = database.stops(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudieron leer los stops: %s", e)
        return pendientes

    salen = []
    for a in pendientes:
        nuevo = None
        # Los puestos antes de guardar el % lo llevan en la nota.
        porcentaje = porcentajes.get(a.id, stop.porcentaje_de_nota(a.nota))
        if porcentaje is not None:
            nuevo = stop.seguir(a.objetivo, porcentaje, a.coin_id, list(config.cartera))
        if nuevo is None:
            salen.append(a)
            continue
        try:
            database.subir_puntual(config.database_path, a.id, nuevo)
        except database.DatabaseError as e:
            logger.error("No se pudo mover el stop %d: %s", a.id, e)
            salen.append(a)
            continue
        logger.info("Stop %d se mueve a %s con el precio medio", a.id, nuevo)
        salen.append(replace(a, objetivo=nuevo))
    return salen


def _calma(config: Config, argumento: str) -> str:
    if argumento:
        ids = [simbolos.a_id(p) for p in argumento.split()]
    else:
        ids = [w.coin_id for w in _con_cambios(config).watchlist]
    if not ids:
        return "¿De cuál? Por ejemplo: /tormenta bitcoin"
    return alerts.formatear_calma([(c, _calma_de(config, c)) for c in ids])


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

    if not telegram.set_commands(config.telegram_token, comandos.MENU):
        logger.warning("No se pudo poner el menu de comandos en Telegram")
    avisar_encendido(config)

    while True:
        try:
            estado, problema = ejecutar_ciclo(config, estado, sin_precio)
            fallos = 0
            fin_del_silencio(config)
            resumen_diario(config)
            resumen_semanal(config)
            resumen_mensual(config)
            resumen_anual(config)
            aviso_compensar(config)
            recordatorios(config)
            programados(config)
            pensados(config)
            cerrar_predicciones(config)
            copia_semanal(config)
            foto_dominancia(config)
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

    if mensaje.get("document"):
        recibir_archivo(config, mensaje["document"])
        return

    logger.info("Comando recibido: %s", texto)
    contestar(config, texto)


def recibir_archivo(config: Config, documento: dict) -> None:
    """Un archivo en el chat: solo sé qué hacer con el CSV de Binance."""
    nombre = documento.get("file_name") or ""
    logger.info("Archivo recibido: %s", nombre)
    contenido = None
    if not nombre.lower().endswith(".csv"):
        respuesta = "Solo sé leer el CSV de Binance. Mira /importar"
    elif (documento.get("file_size") or 0) > MAX_CSV:
        respuesta = "Ese CSV es demasiado grande. Mira /importar"
    else:
        contenido = telegram.descargar(config.telegram_token, documento["file_id"])
        respuesta = "No he podido bajar el archivo. Prueba otra vez."

    if contenido is not None:
        try:
            respuesta = _preparar_importacion(
                config, contenido.decode("utf-8-sig", errors="replace")
            )
        except database.DatabaseError as e:
            logger.error("Error de la base de datos leyendo el CSV: %s", e)
            respuesta = "⚠️ Algo ha fallado con la base de datos. Mira el log."

    teclado = None
    if isinstance(respuesta, comandos.ConBotones):
        respuesta, teclado = respuesta.texto, respuesta.botones
    telegram.send_message(
        config.telegram_token, config.telegram_chat_id, respuesta, botones=teclado
    )


def _preparar_importacion(config: Config, texto: str) -> str | comandos.ConBotones:
    global _importacion
    try:
        lectura = importar.leer_binance(texto, config.vs_currency)
    except importar.ImportarError as e:
        return telegram.escape(str(e))

    ultimo = database.ultimo_movimiento(config.database_path)
    nuevas, repetidas, viejas = [], 0, 0
    for op in lectura.operaciones:
        if database.ya_apuntado(
            config.database_path, op.coin_id, op.tipo, op.cantidad, op.cuando
        ):
            repetidas += 1
        elif ultimo is not None and op.cuando < ultimo:
            viejas += 1
        else:
            nuevas.append(op)

    _importacion = nuevas or None
    texto = alerts.formatear_importacion(
        nuevas,
        lectura.saltadas,
        lectura.sin_comision,
        repetidas,
        viejas,
        ultimo,
        config.vs_currency,
    )
    if not nuevas:
        return texto
    return comandos.ConBotones(
        texto, [[("📥 Importar", "/importar si"), ("✖️ Cancelar", "/importar no")]]
    )


def _comando_importar(config: Config, argumento: str) -> str:
    global _importacion
    orden = argumento.strip().lower()
    if orden == "no":
        _importacion = None
        return "Vale, no apunto nada."
    if orden != "si":
        return IMPORTAR_AYUDA
    if not _importacion:
        return "No tengo nada pendiente. Mándame primero el CSV de Binance."

    pendientes, _importacion = _importacion, None
    apuntadas = fallidas = 0
    for op in pendientes:
        antes = movimientos.buscar(_con_cambios(config).cartera, op.coin_id)
        try:
            if op.tipo == "compra":
                ahora = movimientos.comprar(antes, op.coin_id, op.cantidad, op.coste)
            else:
                ahora = movimientos.vender(antes, op.coin_id, op.cantidad)
        except movimientos.MovimientoError:
            fallidas += 1
            continue
        database.apuntar_movimiento(
            config.database_path,
            op.coin_id,
            op.tipo,
            op.cantidad,
            op.coste,
            antes,
            ahora,
            "Binance",
            op.comision,
            cuando=op.cuando,
        )
        apuntadas += 1
    logger.info("Importadas %d de Binance, %d sin apuntar", apuntadas, fallidas)
    return alerts.formatear_importada(apuntadas, fallidas)


IMPORTAR_AYUDA = (
    "📥 <b>Importar de Binance</b>\n"
    "1. En Binance: Órdenes → Historial de operaciones → Exportar\n"
    "2. Mándame aquí el CSV como archivo\n"
    "3. Te digo lo que he leído y, si te cuadra, pulsas Importar"
)


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


def responder(config: Config, nombre: str, argumento: str) -> Respuesta:
    """El texto con el que se contesta a cada comando."""
    hacer = COMANDOS.get(nombre)
    if hacer is None:
        return comandos.no_entiendo(nombre, telegram.escape(argumento))
    return hacer(config, argumento)


def _con_cartera(hacer: Callable[[Config, str], Respuesta]):
    """Los que no tienen sentido sin cartera; mira antes si has cambiado algo."""

    def con_cartera(config: Config, argumento: str) -> Respuesta:
        config = _con_cambios(config)
        if not config.cartera:
            return SIN_CARTERA
        return hacer(config, argumento)

    return con_cartera


def _comando_mute(config: Config, argumento: str) -> Respuesta:
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


def _comando_unmute(config: Config, argumento: str) -> Respuesta:
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
    if not estaba and not calladas:
        return "No estaba callado."
    desde = database.acabar_silencio(config.database_path) if estaba else None
    if desde is None:
        return "🔔 Vuelvo a avisar."
    return "🔔 Vuelvo a avisar.\n\n" + _lo_perdido(config, desde)


def _comando_semana(config: Config, argumento: str) -> Respuesta:
    # De una sola es lo mismo que su histórico de 7 días: no lo duplico.
    if len(argumento.split()) > 1:
        return "De una en una. Por ejemplo: /semana bitcoin"
    if argumento:
        return _historico(config, f"{argumento} 7d")
    return _semana(config)


def _comando_consultas(config: Config, argumento: str) -> Respuesta:
    apuntar_consultas(config)
    ahora = datetime.now(timezone.utc)
    total = database.get_consultas(config.database_path, cuota.mes(ahora))
    return cuota.mensaje_estado(total, ahora)


def _comando_bot(config: Config, argumento: str) -> Respuesta:
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


def _comando_horoscopo(config: Config, argumento: str) -> Respuesta:
    try:
        signo = horoscopo.interpretar(argumento)
    except horoscopo.HoroscopoError as e:
        return telegram.escape(str(e))
    return alerts.formatear_horoscopo(horoscopo.leer(signo, date.today()))


def _comando_bola(config: Config, argumento: str) -> Respuesta:
    try:
        pregunta = bola.interpretar(argumento)
    except bola.BolaError as e:
        return telegram.escape(str(e))
    return alerts.formatear_bola(pregunta, bola.agitar())


def _comando_quiz(config: Config, argumento: str) -> Respuesta:
    elegida = quiz.interpretar(argumento)
    if elegida is None:
        return comandos.ConBotones(*alerts.formatear_quiz(quiz.sacar()))
    return comandos.ConBotones(*alerts.formatear_respuesta_quiz(*elegida))


def _comando_ppt(config: Config, argumento: str) -> Respuesta:
    try:
        tuya = ppt.interpretar(argumento)
    except ppt.PptError as e:
        return telegram.escape(str(e))
    del_bot = ppt.sacar()
    return alerts.formatear_ppt(tuya, del_bot, ppt.resultado(tuya, del_bot))


def _comando_copia(config: Config, argumento: str) -> Respuesta:
    actual = _con_cambios(config)
    return alerts.formatear_copia(
        copia.lineas(actual.watchlist, actual.cartera, actual.resumen_diario)
    )


def _comando_buscar(config: Config, argumento: str) -> Respuesta:
    if not argumento:
        return "¿Qué busco? Por ejemplo: /buscar btc"
    try:
        resultados = coingecko.buscar(argumento)
    except coingecko.CoinGeckoError as e:
        return f"No he podido buscar ahora mismo: {telegram.escape(str(e))}"
    if not resultados:
        return alerts.formatear_busqueda(argumento, resultados)
    return alerts.con_fuente(alerts.formatear_busqueda(argumento, resultados))


# Cada comando de Telegram y lo que hace. Las lambdas buscan la función al
# llamarla, así los tests pueden cambiarlas con monkeypatch.
COMANDOS: dict[str, Callable[[Config, str], Respuesta]] = {
    "ayuda": lambda c, a: comandos.ayuda(a),
    "status": _comando_status,
    "resumen": _comando_resumen,
    "mute": _comando_mute,
    "unmute": _comando_unmute,
    "horario": lambda c, a: _horario(c, a),
    "semana": _comando_semana,
    "cartera": _con_cartera(lambda c, a: _cartera(c, a)),
    "tarjeta": lambda c, a: _tarjeta(c, a),
    "reparto": _con_cartera(lambda c, a: _reparto(c)),
    "riesgo": _con_cartera(lambda c, a: _riesgo(c)),
    "rebalanceo": _con_cartera(lambda c, a: _rebalanceo(c, a)),
    "compra": lambda c, a: _comprar(c, a),
    "importar": _comando_importar,
    "venta": lambda c, a: _vender(c, a),
    "recompensa": lambda c, a: _recompensa(c, a),
    "corregir": lambda c, a: _corregir(c, a),
    "movimientos": lambda c, a: _movimientos(c, a),
    "primera": lambda c, a: _primera(c, a),
    "pelotazo": lambda c, a: _pelotazo(c),
    "apodo": lambda c, a: _apodo(c),
    "ganancias": lambda c, a: _ganancias(c),
    "arrepentido": lambda c, a: _arrepentido(c),
    "impuestos": lambda c, a: _impuestos(c, a),
    "sivendo": lambda c, a: _sivendo(c, a),
    "permuta": lambda c, a: _permuta(c, a),
    "compensar": lambda c, a: _compensar(c),
    "modelo721": lambda c, a: _modelo721(c),
    "deshacer": lambda c, a: _deshacer(c, a),
    "historico": lambda c, a: _historico(c, a),
    "alerta": lambda c, a: _crear_alerta(c, a),
    "recordar": lambda c, a: _recordar(c, a),
    "cada": lambda c, a: _cada(c, a),
    "rezagada": lambda c, a: _rezagada(c, a),
    "pienso": lambda c, a: _pienso(c, a),
    "prediccion": lambda c, a: _prediccion(c, a),
    "fantasma": lambda c, a: _fantasma(c, a),
    "emocion": lambda c, a: _emocion(c, a),
    "emociones": lambda c, a: _emociones(c),
    "tormenta": lambda c, a: _calma(c, a),
    "herencia": lambda c, a: _herencia(c, a),
    "escalera": _con_cartera(lambda c, a: _escalera(c, a)),
    "stop": _con_cartera(lambda c, a: _stop(c, a)),
    "vigilar": _comando_vigilar,
    "dejar": lambda c, a: _dejar(c, simbolos.varias(a)),
    "alertas": lambda c, a: _alertas(c),
    "quitar": _comando_quitar,
    "consultas": _comando_consultas,
    "bot": _comando_bot,
    "precio": lambda c, a: _precio(c, a),
    "convertir": lambda c, a: _convertir(c, a),
    "exportar": lambda c, a: _exportar(c, a),
    "si": lambda c, a: _si(c, a),
    "dca": lambda c, a: _dca(c, a),
    "objetivo": lambda c, a: _objetivo(c, a),
    "promediar": lambda c, a: _promediar(c, a),
    "posicion": lambda c, a: _posicion(c, a),
    "plan": lambda c, a: _plan(c, a),
    "apy": lambda c, a: _apy(c, a),
    "limite": lambda c, a: _limite(c, a),
    "meta": lambda c, a: _meta(c, a),
    "mes": lambda c, a: _mes(c),
    "anual": lambda c, a: _anual(c, a),
    "hodl": lambda c, a: _hodl(c),
    "record": lambda c, a: _record(c),
    "vsbtc": lambda c, a: _vsbtc(c),
    "vsbolsa": lambda c, a: _vsbolsa(c, a),
    "comisiones": lambda c, a: _comisiones(c, a),
    "deposito": lambda c, a: _deposito(c, a),
    "compras": lambda c, a: _compras(c, a),
    "timing": lambda c, a: _timing(c, a),
    "calendario": lambda c, a: _calendario(c, a),
    "rentabilidad": lambda c, a: _rentabilidad(c),
    "ath": lambda c, a: _ath(c, a),
    "tendencias": lambda c, a: _tendencias(c),
    "dominancia": lambda c, a: _dominancia(c),
    "mercado": lambda c, a: _mercado(c),
    "top": lambda c, a: _top(c),
    "aleatoria": lambda c, a: _aleatoria(c),
    "glosario": lambda c, a: alerts.formatear_glosario(a),
    "frase": lambda c, a: alerts.formatear_frase(frase.elegir()),
    "consejo": lambda c, a: alerts.formatear_consejo(consejo.elegir()),
    "excusa": lambda c, a: alerts.formatear_excusa(excusa.elegir()),
    "refran": lambda c, a: alerts.formatear_refran(refran.elegir()),
    "horoscopo": _comando_horoscopo,
    "galleta": lambda c, a: alerts.formatear_galleta(galleta.abrir(date.today())),
    "tarot": lambda c, a: alerts.formatear_tarot(tarot.sacar()),
    "bola": _comando_bola,
    "version": lambda c, a: alerts.formatear_version(version.leer()),
    "chiste": lambda c, a: alerts.formatear_chiste(chiste.elegir()),
    "dato": lambda c, a: alerts.formatear_dato(dato.elegir()),
    # Lee la cripto igual que /caraocruz, así que uso su misma función.
    "dado": lambda c, a: alerts.formatear_dado(dado.tirar(), caraocruz.interpretar(a)),
    "caraocruz": lambda c, a: alerts.formatear_caraocruz(
        caraocruz.lanzar(), caraocruz.interpretar(a)
    ),
    "adivina": lambda c, a: _adivina(c, a),
    "quiz": _comando_quiz,
    "ppt": _comando_ppt,
    "ultimo": lambda c, a: _ultimo(c),
    "miedo": lambda c, a: _miedo(),
    "sesgo": lambda c, a: _sesgo(c),
    "direccion": lambda c, a: _direccion(c, a),
    "estacional": lambda c, a: _estacional(c, a),
    "funding": lambda c, a: _funding(c, a),
    "comisionred": lambda c, a: _comisionred(c),
    "comparar": lambda c, a: _comparar(c, a),
    "quieta": lambda c, a: _quieta(c),
    "volatilidad": lambda c, a: _volatilidad(c, a),
    "ruido": lambda c, a: _ruido(c, a),
    "soporte": lambda c, a: _soporte(c, a),
    "rango": lambda c, a: _rango(c, a),
    "racha": lambda c, a: _racha(c, a),
    "caida": lambda c, a: _caida(c, a),
    "backtest": lambda c, a: _backtest(c, a),
    "sube": lambda c, a: _sube(c, a),
    "verdes": lambda c, a: _verdes(c, a),
    "extremo": lambda c, a: _extremo(c, a),
    "diames": lambda c, a: _diames(c, a),
    "diasemana": lambda c, a: _diasemana(c, a),
    "horas": lambda c, a: _horas(c, a),
    "ratio": lambda c, a: _ratio(c, a),
    "hoy": lambda c, a: _hoy(c, a),
    "equilibrio": lambda c, a: _equilibrio(c),
    "doble": lambda c, a: _doble(c),
    "mitad": lambda c, a: _mitad(c),
    "sharpe": lambda c, a: _sharpe(c, a),
    "futuro": lambda c, a: _futuro(c, a),
    "inflacion": lambda c, a: _inflacion(c),
    "fibonacci": lambda c, a: _fibonacci(c, a),
    "macd": lambda c, a: _macd(c, a),
    "estocastico": lambda c, a: _estocastico(c, a),
    "bollinger": lambda c, a: _bollinger(c, a),
    "rsi": lambda c, a: _rsi(c, a),
    "rellenar": lambda c, a: _rellenar(c, a),
    "backup": lambda c, a: _backup(c),
    "cuando": lambda c, a: _cuando(c, a),
    "redondo": lambda c, a: _redondo(c, a),
    "dia": lambda c, a: _dia(c, a),
    "correlacion": lambda c, a: _correlacion(c, a),
    "halving": lambda c, a: alerts.formatear_halving(halving.calcular(date.today())),
    "cumple": lambda c, a: alerts.formatear_cumple(cumple.Cumple(date.today())),
    "whitepaper": lambda c, a: alerts.formatear_whitepaper(
        whitepaper.Whitepaper(date.today())
    ),
    "merge": lambda c, a: alerts.formatear_merge(merge.Merge(date.today())),
    "ethereum": lambda c, a: alerts.formatear_ethereum(ethereum.Ethereum(date.today())),
    "adios": lambda c, a: alerts.formatear_adios(adios.Adios(date.today())),
    "ajustes": lambda c, a: ajustes.mensaje(_con_cambios(c)),
    "copia": _comando_copia,
    "media": lambda c, a: _media(c, a),
    "buscar": _comando_buscar,
    **comparaciones.COMANDOS,
}


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


def _cada(config: Config, argumento: str) -> str:
    lista = database.get_programados(config.database_path)
    if not argumento:
        return alerts.formatear_programados(lista)
    try:
        numero = cada.para_quitar(argumento)
        if numero is None:
            dia, hora, comando = cada.interpretar(argumento)
    except cada.CadaError as e:
        return telegram.escape(str(e))

    if numero is not None:
        if database.quitar_programado(config.database_path, numero):
            return f"Hecho, quitado el {numero}."
        return "No tienes ninguno con ese número. Mira /cada"

    nombre, _ = comandos.interpretar(comando)
    if nombre not in COMANDOS:
        return f"No conozco {telegram.escape(comando.split()[0])}. Mira /ayuda"
    if len(lista) >= cada.MAXIMO:
        return f"Ya tienes {cada.MAXIMO}, quita alguno antes: /cada"

    numero = max((p.numero for p in lista), default=0) + 1
    p = cada.Programado(numero, dia, hora, comando)
    database.guardar_programado(config.database_path, p)
    logger.info("Programado %d: %s %s", numero, p.cuando, comando)
    return (
        f"⏰ Hecho: {p.cuando} te mando {telegram.escape(comando)}.\n"
        f"Para quitarlo: /cada quitar {numero}"
    )


def programados(config: Config, ahora: datetime | None = None) -> None:
    """Los de /cada que tocan ahora, como si los hubieras escrito tú."""
    ahora = ahora or datetime.now().astimezone()
    if _silenciado(config):
        return
    try:
        tocan = [
            p
            for p in database.get_programados(config.database_path)
            if cada.toca(p, ahora)
        ]
    except database.DatabaseError as e:
        logger.error("No se pudieron leer los de /cada: %s", e)
        return
    for p in tocan:
        # Apuntado antes de mandarlo: si el comando revienta, que no se repita
        # en cada vuelta hasta pasadas las dos horas.
        database.guardar_programado(
            config.database_path, replace(p, ultimo=ahora.date())
        )
        logger.info("Toca el /cada %d: %s", p.numero, p.comando)
        try:
            contestar(config, p.comando)
        except Exception:
            logger.exception("Error con el /cada %d", p.numero)


def _herencia(config: Config, argumento: str) -> str | comandos.Archivo:
    try:
        orden = herencia.interpretar(argumento)
    except herencia.HerenciaError as e:
        return telegram.escape(str(e))

    if orden[0] == "nota":
        database.guardar_herencia(
            config.database_path, database.NOTA_HERENCIA, orden[1]
        )
        if orden[1] is None:
            return "Hecho, quitada la nota."
        return "📝 Apuntada la nota. Sale en /herencia, debajo de lo que tienes."
    if orden[0] == "donde":
        coin_id, texto = orden[1], orden[2]
        database.guardar_herencia(config.database_path, coin_id, texto)
        nombre = telegram.escape(coin_id)
        if texto is None:
            return f"Hecho, ya no digo dónde está <b>{nombre}</b>."
        return f"📍 Apuntado dónde está <b>{nombre}</b>. Míralo con /herencia"

    cartera = list(_con_cambios(config).cartera)
    if not cartera:
        return (
            "No tienes nada en la cartera. Apunta lo que tienes con /compra "
            "bitcoin 0.016 1000 y luego dónde está con /herencia btc Ledger"
        )
    donde, nota = database.get_herencia(config.database_path)
    precios = _consultar(config, [p.coin_id for p in cartera]) or {}
    lista = herencia.lineas(cartera, precios, donde)
    hoy = date.today()
    papel = alerts.documento_herencia(lista, nota, hoy, config.vs_currency)
    return comandos.Archivo(
        papel.encode(),
        herencia.nombre_archivo(hoy),
        alerts.pie_herencia(lista, hoy),
        f"<pre>{telegram.escape(papel)}</pre>",
    )


def _emocion(config: Config, argumento: str) -> str:
    try:
        numero, cual = emocion.interpretar(argumento)
    except emocion.EmocionError as e:
        return telegram.escape(str(e))
    if not database.apuntar_emocion(config.database_path, numero, cual):
        return f"No tengo ningún movimiento con el número {numero}. Mira /movimientos"
    icono = emocion.EMOCIONES[cual][0]
    return (
        f"{icono} Apuntado: la {numero} fue con {emocion.en_frase(cual)}. Cuando "
        "haya unas cuantas, /emociones te dice con cuál te va mejor"
    )


def _emociones(config: Config) -> str:
    todos = database.get_movimientos(config.database_path, None)
    if not any(m.emocion for m in todos):
        return (
            "Aún no has dicho con qué ánimo compras o vendes. Al apuntar una /compra "
            "o /venta salen unos botones; para las de antes: /emocion 12 miedo "
            "(el número sale en /movimientos)"
        )
    ids = list(dict.fromkeys(m.coin_id for m in todos if m.emocion))
    # Sin precios sale igual, solo que sin cómo van.
    precios = _consultar(config, ids) or {}
    texto = alerts.formatear_emociones(emocion.calcular(todos, precios))
    return alerts.con_fuente(texto) if precios else texto


def _fantasma(config: Config, argumento: str) -> str:
    try:
        orden = fantasma.interpretar(argumento)
    except fantasma.FantasmaError as e:
        return telegram.escape(str(e))
    f = database.get_fantasma(config.database_path)

    if orden[0] == "ver" and f is None:
        return (
            "👻 Aún no tienes cartera fantasma. Tienes 1.000 de mentira para "
            "probar: /fantasma compra btc 200. Para empezar con otra cifra: "
            "/fantasma reinicia 5000"
        )
    if orden[0] == "ver":
        ids = [*f.posiciones, fantasma.BITCOIN]
        precios = _consultar(config, list(dict.fromkeys(ids))) or {}
        return alerts.con_fuente(
            alerts.formatear_fantasma(f, precios, config.vs_currency)
        )

    coin_id = fantasma.BITCOIN if orden[0] == "reinicia" else orden[1]
    try:
        precios = coingecko.get_prices(
            list(dict.fromkeys([coin_id, fantasma.BITCOIN])), config.vs_currency
        )
    except coingecko.CoinGeckoError as e:
        return f"No he podido consultar el precio: {telegram.escape(str(e))}"
    ahora = datetime.now(timezone.utc)

    if orden[0] == "reinicia":
        nueva = fantasma.nueva(orden[1], ahora, precios.get(fantasma.BITCOIN))
        database.guardar_fantasma(config.database_path, nueva)
        return alerts.formatear_fantasma_nueva(orden[1], config.vs_currency)

    precio = precios.get(coin_id)
    if precio is None:
        return (
            f"No encuentro <b>{telegram.escape(coin_id)}</b> en CoinGecko. "
            f"Prueba con /buscar {telegram.escape(coin_id)}"
        )
    f = f or fantasma.nueva(fantasma.INICIAL, ahora, precios.get(fantasma.BITCOIN))
    try:
        if orden[0] == "compra":
            f = fantasma.comprar(f, coin_id, orden[2], precio)
            euros = orden[2]
        else:
            f, euros = fantasma.vender(f, coin_id, orden[2], precio)
    except fantasma.FantasmaError as e:
        return telegram.escape(str(e))

    database.guardar_fantasma(config.database_path, f)
    return alerts.con_fuente(
        alerts.formatear_operacion_fantasma(
            orden[0] == "compra", coin_id, euros, precio, f, config.vs_currency
        )
    )


def _estacional(config: Config, argumento: str) -> str:
    if len(argumento.split()) > 1:
        return "De una en una. Por ejemplo: /estacional btc"
    if argumento:
        coin_id = simbolos.a_id(argumento)
    else:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return "¿De cuál? Por ejemplo: /estacional btc"
        coin_id = vigiladas[0].coin_id

    try:
        velas = estacional.pedir(funding.par(coin_id, argumento))
    except estacional.EstacionalError as e:
        if str(e) == "sin datos":
            return (
                f"Binance no tiene <b>{telegram.escape(coin_id)}</b> contra el dólar. "
                "Prueba con su símbolo, como /estacional btc"
            )
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"

    resultado = estacional.calcular(estacional.leer(velas, datetime.now(timezone.utc)))
    if resultado is None:
        return (
            f"<b>{telegram.escape(coin_id)}</b> lleva muy poco en Binance: aún no "
            "tiene ningún mes entero"
        )
    return alerts.formatear_estacional(coin_id, resultado)


def _sesgo(config: Config) -> str:
    todos = database.get_movimientos(config.database_path, None)
    if not todos:
        return (
            "No has apuntado ninguna compra ni venta por aquí, y lo del PORTFOLIO "
            f"del .env no lleva fecha. Apúntalas así: {movimientos.EJEMPLO_COMPRA}"
        )
    hoy = datetime.now(timezone.utc).date()
    try:
        indices = miedo.historico(sesgo.dias_hacia_atras(todos, hoy))
    except miedo.MiedoError as e:
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"

    # Sin precios de hoy sale igual, solo que sin el «hoy» de cada grupo.
    precios = _consultar(config, list({m.coin_id for m in todos})) or {}
    resultado = sesgo.calcular(todos, indices, precios)
    if resultado.compras is None and resultado.ventas is None:
        return (
            "alternative.me no tiene el índice de los días de tus compras y ventas. "
            "Prueba en un rato"
        )
    texto = alerts.formatear_sesgo(resultado)
    return alerts.con_fuente(texto) if precios else texto


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


def _ruido(config: Config, argumento: str) -> str:
    try:
        coin_id, horas = ruido.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))

    vigiladas = _con_cambios(config).watchlist
    if coin_id:
        vigiladas = [w for w in vigiladas if w.coin_id == coin_id]
        if not vigiladas:
            return (
                f"No vigilo <b>{telegram.escape(coin_id)}</b>, así que no te ha "
                "avisado nunca. Lo que vigilo: /vigilar"
            )
    if not vigiladas:
        return "No vigilo ninguna. Empieza con /vigilar bitcoin %5"

    lista, primero = [], None
    for w in vigiladas:
        serie = database.get_serie(
            config.database_path, w.coin_id, horas, config.vs_currency
        )
        lista.append(ruido.analizar(serie, w))
        if serie and (primero is None or serie[0][0] > primero):
            primero = serie[0][0]

    if primero is None:
        return "Aún no tengo precios guardados. Vuelve en un rato o usa /rellenar"
    falta = periodo.falta_principio(primero, datetime.now(timezone.utc), horas)
    return alerts.formatear_ruido(
        lista, horas, config.vs_currency, primero if falta else None
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


def _lo_perdido(config: Config, desde: datetime) -> str:
    config = _con_cambios(config)
    ahora = datetime.now(timezone.utc)
    horas = (ahora - desde).total_seconds() / 3600
    coin_ids = [w.coin_id for w in config.watchlist]
    series = {
        c: database.get_serie(config.database_path, c, horas, config.vs_currency)
        for c in coin_ids
    }
    posiciones = list(config.cartera)
    serie_cartera = []
    if posiciones:
        filas = database.get_series(
            config.database_path,
            [p.coin_id for p in posiciones],
            horas,
            config.vs_currency,
        )
        serie_cartera = cartera.serie_valor(posiciones, filas)
    resultado = perdido.calcular(desde, ahora, series, serie_cartera)
    return alerts.formatear_perdido(
        resultado, config.vs_currency, salud.cuanto(resultado.tiempo)
    )


def fin_del_silencio(config: Config) -> None:
    """Si el silencio se acabó solo, lo que te has perdido. Con /unmute va en él."""
    try:
        desde = database.inicio_silencio(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudo leer el inicio del silencio: %s", e)
        return
    if desde is None or _silenciado(config):
        return

    try:
        texto = "🔔 <b>Se acabó el silencio</b>, vuelvo a avisar.\n\n" + _lo_perdido(
            config, desde
        )
    except database.DatabaseError as e:
        logger.error("No se pudo mirar lo que pasó mientras callaba: %s", e)
        return
    if not telegram.send_message(config.telegram_token, config.telegram_chat_id, texto):
        logger.error("No se pudo contar lo que pasó mientras callaba, lo reintento")
        return
    try:
        database.acabar_silencio(config.database_path)
    except database.DatabaseError as e:
        logger.error("No se pudo apuntar el final del silencio: %s", e)


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


def datos_panel(config: Config) -> panel.Panel:
    """Lo que sale en el panel, todo de la base de datos: no gasta consultas."""
    config = _con_cambios(config)
    posiciones = list(config.cartera)
    pendientes = database.get_puntuales(config.database_path, config.vs_currency)
    ids = [p.coin_id for p in posiciones] + [w.coin_id for w in config.watchlist]
    ids += [a.coin_id for a in pendientes if a.coin_id != puntuales.CARTERA]
    ids = list(dict.fromkeys(ids))

    precios, antes = {}, {}
    for coin_id in ids:
        precio = database.get_last_price(config.database_path, coin_id)
        if precio is not None:
            precios[coin_id] = precio
        hace_un_dia = database.get_price_at(config.database_path, coin_id, 24)
        if hace_un_dia is not None:
            antes[coin_id] = hace_un_dia

    lineas: dict[str, list[float]] = {}
    for _, coin_id, precio in database.get_series(
        config.database_path, ids, 24, config.vs_currency
    ):
        lineas.setdefault(coin_id, []).append(precio)

    filas, faltan = panel.filas_cartera(posiciones, precios, antes, lineas)
    serie = cartera.serie_valor(
        posiciones,
        database.get_series(
            config.database_path,
            [p.coin_id for p in posiciones],
            24 * 7,
            config.vs_currency,
        ),
    )
    vigiladas_ = [
        panel.Vigilada(
            w.coin_id,
            w,
            precios.get(w.coin_id),
            panel.cambio(precios.get(w.coin_id), antes.get(w.coin_id)),
            panel.muestrear(lineas.get(w.coin_id, []), panel.PUNTOS_MINI),
        )
        for w in config.watchlist
    ]
    return panel.Panel(
        config.vs_currency,
        filas,
        vigiladas_,
        panel.alertas(pendientes, precios, cartera.valor_total(posiciones, precios)),
        serie,
        database.ultimo_guardado(config.database_path),
        faltan,
        panel.total_antes(posiciones, antes),
    )


def pagina_panel(config: Config) -> str:
    datos = datos_panel(config)
    ahora = datetime.now(timezone.utc)
    return panel_html.pagina(
        datos, ahora, panel.parado(datos.actualizado, ahora, config.check_interval)
    )


def servir_panel(config: Config, puerto: int) -> int:
    """El panel en http://127.0.0.1:puerto hasta que lo pares con Ctrl+C."""

    class Atender(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.split("?")[0] != "/":
                self.send_error(404)
                return
            try:
                cuerpo = pagina_panel(config).encode()
            except database.DatabaseError as e:
                logger.error("No se pudo montar el panel: %s", e)
                self.send_error(500, "No se pudo leer la base de datos")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(cuerpo)

        def log_message(self, formato: str, *args) -> None:
            logger.debug("Panel: " + formato, *args)

    # Solo en este ordenador: el panel enseña tu cartera y no pide contraseña.
    try:
        servidor = HTTPServer(("127.0.0.1", puerto), Atender)
    except OSError as e:
        logger.error("No se pudo abrir el panel en el puerto %d: %s", puerto, e)
        return 1
    logger.info("Panel en http://127.0.0.1:%d (Ctrl+C para pararlo)", puerto)
    try:
        servidor.serve_forever()
    finally:
        servidor.server_close()
    return 0


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
    parser.add_argument(
        "--panel",
        nargs="?",
        const=8000,
        type=int,
        metavar="PUERTO",
        help="abre el panel web en http://127.0.0.1:8000 (u otro puerto)",
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

    if args.panel:
        return servir_panel(config, args.panel)

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
