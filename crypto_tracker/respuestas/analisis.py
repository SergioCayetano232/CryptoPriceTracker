"""Lo que se mira en el histórico de una cripto: RSI, medias, rachas, soportes..."""

from datetime import datetime, timezone

from .. import (
    alerts,
    backtest,
    bollinger,
    caida,
    cartera,
    correlacion,
    cuando,
    database,
    diames,
    diasemana,
    estocastico,
    fibonacci,
    futuro,
    horas,
    macd,
    media,
    mejor,
    periodo,
    puntuales,
    racha,
    rango,
    ratio,
    rsi,
    sharpe,
    simbolos,
    soporte,
    sube,
    telegram,
    verdes,
    volatilidad,
)
from ..config import Config
from .base import (
    SIN_CARTERA,
    _con_cambios,
    _valor_guardado,
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
