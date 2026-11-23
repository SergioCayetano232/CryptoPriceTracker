"""Lo que se mira en el histórico de una cripto: RSI, medias, rachas, soportes..."""

import logging
from datetime import date, datetime, timedelta, timezone

from .. import (
    alerts,
    backtest,
    bollinger,
    botones,
    caida,
    calendario,
    cartera,
    comandos,
    comparar,
    correlacion,
    cuando,
    database,
    dca,
    diames,
    diasemana,
    estacional,
    estocastico,
    fibonacci,
    funding,
    futuro,
    grafica,
    horas,
    hubiera,
    macd,
    media,
    mejor,
    miedo,
    periodo,
    puntuales,
    quieta,
    racha,
    rango,
    ratio,
    rsi,
    ruido,
    semaforo,
    sharpe,
    simbolos,
    soporte,
    sube,
    telegram,
    verdes,
    volatilidad,
    voto,
)
from ..config import Config
from .base import (
    SIN_CARTERA,
    _con_cambios,
    _valor_guardado,
)
from .revisiones import _calma_de

logger = logging.getLogger("crypto_tracker")


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


def _soporte(config: Config, argumento: str) -> str:
    try:
        coin_id, horas = soporte.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {soporte.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    resultado = soporte.calcular(serie)
    if resultado is None:
        return (
            f"Necesito al menos 5 días guardados de <b>{telegram.escape(coin_id)}</b> "
            f"({periodo.nombre(horas)}). Con /rellenar {telegram.escape(coin_id)} "
            "bajo los que faltan"
        )
    return alerts.formatear_soporte(coin_id, resultado, horas, config.vs_currency)


def _backtest(config: Config, argumento: str) -> str:
    try:
        coin_id, porcentaje, horas = backtest.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {backtest.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    resultado = backtest.calcular(serie, porcentaje)
    if resultado is None:
        return (
            f"No tengo precios guardados de <b>{telegram.escape(coin_id)}</b> "
            f"({periodo.nombre(horas)}). Solo sé de las que vigilo: míralas "
            "con /vigilar"
        )

    primero = serie[0][0]
    falta = periodo.falta_principio(primero, datetime.now(timezone.utc), horas)
    return alerts.formatear_backtest(
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


def _diames(config: Config, argumento: str) -> str:
    try:
        coin_id, horas = diames.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {diames.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    resultado = diames.calcular(volatilidad.por_dias(serie))
    if resultado is None:
        return (
            f"No tengo un mes seguido de precios de <b>{telegram.escape(coin_id)}</b> "
            f"({periodo.nombre(horas)}). Con /rellenar {telegram.escape(coin_id)} "
            "bajo los que faltan"
        )

    falta = periodo.falta_principio(serie[0][0], datetime.now(timezone.utc), horas)
    return alerts.formatear_diames(coin_id, resultado, falta)


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


def _semaforo(config: Config, argumento: str) -> str:
    if len(argumento.split()) > 1:
        return "De una en una. Por ejemplo: /semaforo bitcoin"
    if argumento:
        coin_id = simbolos.a_id(argumento)
    else:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return "¿De cuál? Por ejemplo: /semaforo bitcoin"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(
        config.database_path, coin_id, rsi.HORAS, config.vs_currency
    )
    dias = volatilidad.por_dias(serie)
    if not dias:
        return (
            f"No tengo precios guardados de <b>{telegram.escape(coin_id)}</b>. "
            "Solo sé de las que vigilo: míralas con /vigilar"
        )

    votos, faltan = [], []
    # Cada uno pide sus días; el que no llega se queda sin votar.
    de_precios = (
        ("el RSI", rsi.calcular(dias), semaforo.de_rsi),
        ("el MACD", macd.calcular(dias), semaforo.de_macd),
        ("las bandas", bollinger.calcular(dias), semaforo.de_bandas),
    )
    for nombre, resultado, votar in de_precios:
        if resultado is None:
            faltan.append(nombre)
        else:
            votos.append(votar(resultado))

    medias = {v: media.calcular(dias, v) for v in media.VENTANAS}
    voto = semaforo.de_medias(dias[-1][1], medias)
    if voto is None:
        faltan.append("las medias")
    else:
        votos.append(voto)

    # Sin días suficientes no merece la pena salir a internet a por lo demás.
    if not votos:
        return (
            f"Me faltan días de <b>{telegram.escape(coin_id)}</b> para el semáforo. "
            f"Con /rellenar {telegram.escape(coin_id)} bajo los que faltan"
        )

    try:
        indices = miedo.pedir()
    except miedo.MiedoError as e:
        logger.warning("El semaforo va sin el miedo: %s", e)
        indices = []
    if indices:
        votos.append(semaforo.de_miedo(indices[0]))
    else:
        faltan.append("el miedo")

    par = funding.par(coin_id, argumento)
    try:
        apuestas = funding.leer(par, *funding.pedir(par))
    except funding.FundingError as e:
        # Lo normal: que no tenga futuros en Binance.
        logger.info("El semaforo va sin el funding de %s: %s", par, e)
        apuestas = None
    if apuestas is None:
        faltan.append("el funding")
    else:
        votos.append(semaforo.de_funding(apuestas))

    luz = semaforo.luz(votos)
    if luz is None:
        return (
            f"Me faltan días de <b>{telegram.escape(coin_id)}</b> para el semáforo. "
            f"Con /rellenar {telegram.escape(coin_id)} bajo los que faltan"
        )
    return alerts.formatear_semaforo(coin_id, votos, luz, faltan)


def _sharpe(config: Config, argumento: str) -> str:
    try:
        dias = sharpe.interpretar(argumento)
    except sharpe.SharpeError as e:
        return telegram.escape(str(e))
    posiciones = list(_con_cambios(config).cartera)
    if not posiciones:
        return SIN_CARTERA

    horas = (dias + 1) * 24
    coin_ids = [p.coin_id for p in posiciones]
    filas = database.get_series(
        config.database_path, coin_ids, horas, config.vs_currency
    )
    serie = cartera.serie_valor(posiciones, filas)
    resultado = sharpe.calcular(volatilidad.por_dias(serie))
    if resultado is None:
        return (
            f"Necesito {sharpe.MIN_CAMBIOS + 1} días seguidos con el precio de todo "
            "lo que tienes, y que se haya movido algo. Con /rellenar bajo los que "
            "faltan"
        )

    # Si solo tienes bitcoin, compararte con él no dice nada.
    btc = None
    if coin_ids != ["bitcoin"]:
        btc = sharpe.calcular(
            volatilidad.por_dias(
                database.get_serie(
                    config.database_path, "bitcoin", horas, config.vs_currency
                )
            )
        )
    return alerts.formatear_sharpe(resultado, btc, dias)


def _futuro(config: Config, argumento: str) -> str:
    try:
        dias = futuro.interpretar(argumento)
    except futuro.FuturoError as e:
        return telegram.escape(str(e))
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor

    posiciones = list(_con_cambios(config).cartera)
    filas = database.get_series(
        config.database_path,
        [p.coin_id for p in posiciones],
        futuro.HORAS,
        config.vs_currency,
    )
    serie = cartera.serie_valor(posiciones, filas)
    resultado = futuro.calcular(valor, volatilidad.por_dias(serie), dias)
    if resultado is None:
        return (
            f"Necesito {futuro.MIN_CAMBIOS + 1} días seguidos con el precio de todo "
            "lo que tienes para saber cuánto se mueve tu cartera. Con /rellenar "
            "bajo los que faltan"
        )
    return alerts.formatear_futuro(resultado, config.vs_currency)


def _fibonacci(config: Config, argumento: str) -> str:
    try:
        coin_id, horas = fibonacci.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if not coin_id:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {fibonacci.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(config.database_path, coin_id, horas, config.vs_currency)
    resultado = fibonacci.calcular(serie)
    if resultado is None:
        if len(serie) < 2:
            return (
                f"No tengo precios guardados de <b>{telegram.escape(coin_id)}</b> "
                f"({periodo.nombre(horas)}). Con /rellenar {telegram.escape(coin_id)} "
                "bajo los que faltan"
            )
        return (
            f"<b>{telegram.escape(coin_id)}</b> apenas se ha movido "
            f"({periodo.nombre(horas)}): los niveles saldrían todos pegados"
        )

    primero = serie[0][0]
    falta = periodo.falta_principio(primero, datetime.now(timezone.utc), horas)
    return alerts.formatear_fibonacci(
        coin_id, resultado, horas, config.vs_currency, primero if falta else None
    )


def _macd(config: Config, argumento: str) -> str:
    if len(argumento.split()) > 1:
        return "De una en una. Por ejemplo: /macd bitcoin"
    if argumento:
        coin_id = simbolos.a_id(argumento)
    else:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return "¿De cuál? Por ejemplo: /macd bitcoin"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(
        config.database_path, coin_id, macd.HORAS, config.vs_currency
    )
    resultado = macd.calcular(volatilidad.por_dias(serie))
    if resultado is None:
        return (
            f"Necesito {macd.MINIMO + 1} días seguidos de precios de "
            f"<b>{telegram.escape(coin_id)}</b> y no los tengo. Con /rellenar "
            f"{telegram.escape(coin_id)} bajo los que faltan"
        )
    return alerts.formatear_macd(coin_id, resultado, config.vs_currency)


def _estocastico(config: Config, argumento: str) -> str:
    if len(argumento.split()) > 1:
        return "De una en una. Por ejemplo: /estocastico bitcoin"
    if argumento:
        coin_id = simbolos.a_id(argumento)
    else:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return "¿De cuál? Por ejemplo: /estocastico bitcoin"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(
        config.database_path, coin_id, estocastico.HORAS, config.vs_currency
    )
    resultado = estocastico.calcular(estocastico.velas(serie))
    if resultado is None:
        return (
            f"Necesito {estocastico.MINIMO + 1} días seguidos de precios de "
            f"<b>{telegram.escape(coin_id)}</b> y no los tengo. Con /rellenar "
            f"{telegram.escape(coin_id)} bajo los que faltan"
        )
    return alerts.formatear_estocastico(coin_id, resultado, config.vs_currency)


def _bollinger(config: Config, argumento: str) -> str:
    if len(argumento.split()) > 1:
        return "De una en una. Por ejemplo: /bollinger bitcoin"
    if argumento:
        coin_id = simbolos.a_id(argumento)
    else:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return "¿De cuál? Por ejemplo: /bollinger bitcoin"
        coin_id = vigiladas[0].coin_id

    serie = database.get_serie(
        config.database_path, coin_id, bollinger.HORAS, config.vs_currency
    )
    resultado = bollinger.calcular(volatilidad.por_dias(serie))
    if resultado is None:
        return (
            f"Necesito {bollinger.PERIODO} días seguidos de precios de "
            f"<b>{telegram.escape(coin_id)}</b> y no los tengo. Con /rellenar "
            f"{telegram.escape(coin_id)} bajo los que faltan"
        )
    return alerts.formatear_bollinger(coin_id, resultado, config.vs_currency)


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


def _correlacion(config: Config, argumento: str) -> str | comandos.Foto:
    try:
        ids, horas = correlacion.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    if ids == [correlacion.TODAS]:
        return _correlaciones(_con_cambios(config), horas)
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


def _correlaciones(config: Config, horas: float) -> str | comandos.Foto:
    ids = correlacion.juntar(
        [w.coin_id for w in config.watchlist], [p.coin_id for p in config.cartera]
    )
    if len(ids) < 2:
        return (
            "Solo vigilas una cripto y no hay con qué compararla. Añade otra: /vigilar"
        )
    series = {
        c: volatilidad.por_dias(
            database.get_serie(config.database_path, c, horas, config.vs_currency)
        )
        for c in ids
    }
    m = correlacion.matriz(series)
    if not m.con_valor:
        return (
            f"Necesito al menos {correlacion.MINIMO} días seguidos con precios "
            f"({periodo.nombre(horas)}) de dos de ellas, y no los tengo todavía."
        )
    texto = alerts.formatear_correlaciones(m, horas)
    try:
        png = grafica.dibujar_correlaciones(m, periodo.nombre(horas))
    except Exception as e:
        logger.warning("Mando /correlacion todas sin imagen: %s", e)
        return texto
    return comandos.Foto(png, texto, texto)


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


def _calma(config: Config, argumento: str) -> str:
    if argumento:
        ids = [simbolos.a_id(p) for p in argumento.split()]
    else:
        ids = [w.coin_id for w in _con_cambios(config).watchlist]
    if not ids:
        return "¿De cuál? Por ejemplo: /tormenta bitcoin"
    return alerts.formatear_calma([(c, _calma_de(config, c)) for c in ids])


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


def _comparar(config: Config, argumento: str) -> str | comandos.Foto:
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
    texto = alerts.con_fuente(alerts.formatear_comparar(resultados, sin_datos, horas))
    if len(resultados) > comparar.MAX_GRAFICA:
        return texto
    try:
        png = grafica.dibujar_comparar(comparar.en_base_100(series, resultados), horas)
    except Exception as e:
        logger.warning("Mando /comparar sin imagen: %s", e)
        return texto
    return comandos.Foto(png, texto, texto)


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


def _voto(config: Config, argumento: str) -> str:
    try:
        v = voto.interpretar(argumento)
    except voto.VotoError as e:
        return telegram.escape(str(e))
    database.guardar_voto(config.database_path, v)
    desde = datetime.now(timezone.utc) - timedelta(hours=ruido.POR_DEFECTO)
    suyos = voto.contar(database.get_votos(config.database_path), v.coin_id, desde)
    return alerts.formatear_voto(v.coin_id, v.util, suyos)


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
    votos = database.get_votos(config.database_path)
    desde = datetime.now(timezone.utc) - timedelta(hours=horas)
    for w in vigiladas:
        serie = database.get_serie(
            config.database_path, w.coin_id, horas, config.vs_currency
        )
        lista.append(ruido.analizar(serie, w, voto.contar(votos, w.coin_id, desde)))
        if serie and (primero is None or serie[0][0] > primero):
            primero = serie[0][0]

    if primero is None:
        return "Aún no tengo precios guardados. Vuelve en un rato o usa /rellenar"
    falta = periodo.falta_principio(primero, datetime.now(timezone.utc), horas)
    return alerts.formatear_ruido(
        lista, horas, config.vs_currency, primero if falta else None
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
