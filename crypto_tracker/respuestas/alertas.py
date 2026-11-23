"""Lo que contesta sobre tus alertas: ponerlas, verlas y quitarlas."""

import logging
from datetime import date, datetime, timezone

from .. import (
    alertaratio,
    alerts,
    botones,
    cartera,
    coingecko,
    comandos,
    condicion,
    database,
    escalera,
    impuestos,
    juntas,
    movimientos,
    puntuales,
    rezagada,
    simbolos,
    stop,
    telegram,
    vigiladas,
)
from ..config import Config
from .base import (
    Respuesta,
    _alertas_ratio,
    _con_cambios,
    _medir_pareja,
    _precio_o_pedirlo,
)
from .cartera import _en_negrita, _valor_cartera

logger = logging.getLogger("crypto_tracker")


def _comando_vigilar(config: Config, argumento: str) -> Respuesta:
    return _vigilar(config, argumento) if argumento else _lista_vigiladas(config)


def _comando_quitar(config: Config, argumento: str) -> Respuesta:
    # A secas, la lista con sus 🗑: mas facil que ir a mirar el numero.
    if not argumento:
        return _alertas(config)
    if argumento.lower() == "todas":
        cuantas = database.borrar_puntuales(config.database_path, config.vs_currency)
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
    quitadas = [n for n in numeros if database.borrar_puntual(config.database_path, n)]
    no_estaban = [n for n in numeros if n not in quitadas]
    return alerts.formatear_quitadas(quitadas, no_estaban)


def _alertas(config: Config) -> str | comandos.ConBotones:
    pendientes = database.get_puntuales(config.database_path, config.vs_currency)
    precios = _precios_alertas(config, pendientes)
    pendientes = puntuales.por_cercania(pendientes, precios)
    texto = alerts.formatear_puntuales(
        pendientes,
        config.vs_currency,
        precios,
        parejas=database.parejas(config.database_path),
    )
    if precios:
        texto = alerts.con_fuente(texto)
    de_ratio = _alertas_ratio(config)
    if de_ratio:
        lista = alerts.formatear_alertas_ratio(de_ratio)
        texto = f"{texto}\n\n{lista}" if pendientes else lista
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


def _crear_alerta(config: Config, argumento: str) -> str:
    if alertaratio.es_ratio(argumento):
        return _alerta_ratio(config, argumento)
    try:
        argumento, cond = condicion.separar(argumento)
    except condicion.CondicionError as e:
        return telegram.escape(str(e))
    argumento, otro = puntuales.separar_pareja(argumento)
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
    if otro and relativa:
        return f"Con la «o» van dos precios, no %. Así: {puntuales.EJEMPLO_PAREJA}"

    es_cartera = coin_id == puntuales.CARTERA
    if es_cartera and not _con_cambios(config).cartera:
        return "No tienes cartera. Apunta lo que tienes con /compra bitcoin 0.016 1000"
    if es_cartera and cond and cond.indicador == "rsi":
        return (
            "El RSI es de cada cripto, no de la cartera entera. Con la cartera vale "
            "el miedo: /alerta cartera 10000 si miedo<20"
        )

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
            if otro:
                otro_objetivo = puntuales.otro_de_pareja(otro, objetivo, precio)
        except puntuales.PuntualError as e:
            return telegram.escape(str(e))

    if otro:
        return _crear_pareja(
            config, coin_id, (objetivo, otro_objetivo), precio, horas, nota, cond
        )

    # Con los botones 🎯 y 🔁 es facil pedir dos veces la misma, y luego llegan
    # dos avisos iguales.
    pendientes = database.get_puntuales(config.database_path, config.vs_currency)
    igual = puntuales.repetida(pendientes, coin_id, objetivo, sube)
    if igual and igual.condicion == cond:
        return f"Ya tienes esa alerta, es la número {igual.id}. Mira /alertas"

    alerta = database.crear_puntual(
        config.database_path,
        coin_id,
        objetivo,
        sube,
        config.vs_currency,
        puntuales.caducidad(datetime.now(timezone.utc), horas),
        nota,
        cond,
    )
    logger.info("Alerta %d creada: %s a %s", alerta.id, coin_id, objetivo)
    return alerts.con_fuente(
        alerts.formatear_puntual(alerta, precio, config.vs_currency)
    )


def _crear_pareja(
    config: Config,
    coin_id: str,
    objetivos: tuple[float, float],
    precio: float,
    horas: float | None,
    nota: str | None,
    cond: condicion.Condicion | None,
) -> str:
    """/alerta bitcoin 60000 o 80000: dos alertas, y la que no salte se quita."""
    caduca = puntuales.caducidad(datetime.now(timezone.utc), horas)
    abajo, arriba = (
        database.crear_puntual(
            config.database_path,
            coin_id,
            o,
            o > precio,
            config.vs_currency,
            caduca,
            nota,
            cond,
        )
        for o in sorted(objetivos)
    )
    database.guardar_pareja(config.database_path, abajo.id, arriba.id)
    logger.info("Alertas %d y %d creadas en pareja: %s", abajo.id, arriba.id, coin_id)
    return alerts.con_fuente(
        alerts.formatear_pareja(arriba, abajo, precio, config.vs_currency)
    )


def _alerta_ratio(config: Config, argumento: str) -> str:
    try:
        coin_id, contra, texto = alertaratio.interpretar(argumento)
        if alertaratio.es_quitar(texto):
            if database.quitar_alerta_ratio(config.database_path, coin_id, contra):
                return "Hecho, quitada."
            return "No tenías esa. Mira /alertas"
        valor = alertaratio.objetivo(texto) if texto else None
    except alertaratio.AlertaRatioError as e:
        return telegram.escape(str(e))

    try:
        precios = coingecko.get_prices([coin_id, contra], config.vs_currency)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirar el precio ahora mismo: {telegram.escape(str(e))}"
    falta = next((c for c in (coin_id, contra) if not precios.get(c)), None)
    if falta:
        return (
            f"No encuentro <b>{telegram.escape(falta)}</b> en CoinGecko. "
            f"Prueba con /buscar {telegram.escape(falta)}"
        )
    ahora = precios[coin_id] / precios[contra]
    if valor is None:
        return alerts.formatear_ratio_ahora(coin_id, contra, ahora)

    try:
        a = alertaratio.crear(coin_id, contra, valor, ahora)
    except alertaratio.AlertaRatioError as e:
        return telegram.escape(str(e))
    # Una por pareja: si ya había, la nueva la pisa.
    database.guardar_alerta_ratio(config.database_path, a)
    return alerts.formatear_alerta_ratio(a, ahora)


def _rezagada(config: Config, argumento: str) -> str:
    if not argumento:
        return alerts.formatear_rezagadas(database.get_rezagadas(config.database_path))
    try:
        coin_id, contra, pct = rezagada.interpretar(argumento)
    except rezagada.RezagadaError as e:
        return telegram.escape(str(e))
    una, otra = (f"<b>{telegram.escape(c)}</b>" for c in (coin_id, contra))
    if pct is None:
        if database.quitar_rezagada(config.database_path, coin_id, contra):
            return f"Hecho, ya no comparo {una} con {otra}."
        return "No tenías esa. Mira /rezagada"

    # Solo guardo el histórico de estas: sin él no hay semana con la que comparar.
    config = _con_cambios(config)
    con_historico = {w.coin_id for w in config.watchlist} | {
        p.coin_id for p in config.cartera
    }
    fuera = [c for c in (coin_id, contra) if c not in con_historico]
    if fuera:
        return (
            f"No guardo el precio de <b>{telegram.escape(fuera[0])}</b>. Vigílala "
            f"antes: /vigilar {telegram.escape(fuera[0])} 5%"
        )
    database.guardar_rezagada(
        config.database_path, rezagada.Rezagada(coin_id, contra, pct)
    )
    return f"🐢 Hecho: te aviso si {una} va un {pct:g}% peor que {otra} en 7 días."


def _juntas(config: Config, argumento: str) -> str:
    if not argumento:
        return alerts.formatear_juntas(database.get_juntas(config.database_path))
    try:
        una, otra, quitar = juntas.interpretar(argumento)
    except juntas.JuntasError as e:
        return telegram.escape(str(e))
    nombres = " y ".join(f"<b>{telegram.escape(c)}</b>" for c in (una, otra))
    if quitar:
        if database.quitar_juntas(config.database_path, una, otra):
            return f"Hecho, ya no miro si {nombres} van juntas."
        return "No tenías esa. Mira /juntas"

    # Solo guardo el histórico de estas: sin él no hay con qué compararlas.
    config = _con_cambios(config)
    con_historico = {w.coin_id for w in config.watchlist} | {
        p.coin_id for p in config.cartera
    }
    fuera = [c for c in (una, otra) if c not in con_historico]
    if fuera:
        return (
            f"No guardo el precio de <b>{telegram.escape(fuera[0])}</b>. Vigílala "
            f"antes: /vigilar {telegram.escape(fuera[0])} 5%"
        )

    medida = _medir_pareja(config, una, otra)
    if juntas.van_juntas(medida) is False:
        valor = f"{medida.larga.valor:+.2f}".replace(".", ",")
        return (
            f"{nombres} no van juntas: este mes su correlación es {valor}. No hay "
            f"nada que se pueda romper. Míralo en /correlacion {una} {otra}"
        )
    # Si ya están separadas no aviso de eso: aviso cuando vuelva a pasar.
    _, avisada = juntas.toca(juntas.Pareja(una, otra), medida)
    database.guardar_juntas(config.database_path, juntas.Pareja(una, otra, avisada))
    texto = f"🔗 Hecho: te aviso si {nombres} dejan de ir juntas."
    if juntas.van_juntas(medida) is None:
        texto += (
            f"\n<i>Aún no tengo días para compararlas; hacen falta unos "
            f"{juntas.CORTA}. Con /rellenar los bajo.</i>"
        )
    elif avisada:
        texto += "\n<i>Ahora mismo ya van separadas: te aviso la próxima vez.</i>"
    return texto


def _stop(config: Config, argumento: str) -> str:
    try:
        argumento, movil = stop.separar_movil(argumento)
        coin_id, porcentaje = stop.interpretar(argumento)
    except stop.StopError as e:
        return telegram.escape(str(e))
    if movil and porcentaje > 0:
        return f"El móvil es para cuando baja. Escríbelo así: {stop.EJEMPLO_MOVIL}"

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
    if movil:
        valor = cartera.total(valores) if es_cartera else valores[0]
        return _stop_movil(config, coin_id, porcentaje, valor)

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
    database.guardar_stop(config.database_path, alerta.id, porcentaje)
    logger.info("Stop %d creado: %s a %s", alerta.id, coin_id, s.objetivo)
    return alerts.con_fuente(alerts.formatear_stop(s, alerta.id, config.vs_currency))


def _escalera(config: Config, argumento: str) -> str:
    try:
        coin_id, precios, porcentaje = escalera.interpretar(argumento)
    except escalera.EscaleraError as e:
        return telegram.escape(str(e))
    antes = next((p for p in config.cartera if p.coin_id == coin_id), None)
    if antes is None:
        return (
            f"No tienes <b>{telegram.escape(coin_id)}</b> en la cartera. "
            "Lo que tienes, en /cartera"
        )

    ahora = _precio_o_pedirlo(config, coin_id)
    if isinstance(ahora, str):
        return ahora
    todos = database.get_movimientos(config.database_path, None)
    este_año = impuestos.calcular(todos, date.today().year)
    historia = [m for m in todos if m.coin_id == coin_id]
    try:
        e = escalera.calcular(
            antes, precios, porcentaje, ahora, este_año.ganancia, historia
        )
    except escalera.EscaleraError as error:
        return telegram.escape(str(error))

    pendientes = database.get_puntuales(config.database_path, config.vs_currency)
    for x in e.escalones:
        igual = puntuales.repetida(pendientes, coin_id, x.precio, True)
        if igual:
            return (
                f"Ya tienes una alerta a ese precio, la número {igual.id}. "
                f"Quítala con /quitar {igual.id} o elige otros escalones."
            )

    # Cada escalón es una /alerta más: salta, se lista y se quita como las otras.
    numeros = []
    for i, x in enumerate(e.escalones, 1):
        cantidad = movimientos.texto_cantidad(x.cantidad)
        alerta = database.crear_puntual(
            config.database_path,
            coin_id,
            x.precio,
            True,
            config.vs_currency,
            None,
            escalera.nota(i, len(e.escalones), cantidad),
        )
        numeros.append(alerta.id)
    logger.info("Escalera de %s creada: %s", coin_id, numeros)
    return alerts.con_fuente(alerts.formatear_escalera(e, numeros, config.vs_currency))


def _escalera_compra(config: Config, argumento: str) -> str:
    try:
        coin_id, precios, gasto = escalera.interpretar_compra(argumento)
    except escalera.EscaleraError as e:
        return telegram.escape(str(e))

    ahora = _precio_o_pedirlo(config, coin_id)
    if isinstance(ahora, str):
        return ahora
    antes = movimientos.buscar(config.cartera, coin_id)
    try:
        e = escalera.calcular_compra(coin_id, precios, gasto, ahora, antes)
    except escalera.EscaleraError as error:
        return telegram.escape(str(error))

    pendientes = database.get_puntuales(config.database_path, config.vs_currency)
    for x in e.escalones:
        igual = puntuales.repetida(pendientes, coin_id, x.precio, False)
        if igual:
            return (
                f"Ya tienes una alerta a ese precio, la número {igual.id}. "
                f"Quítala con /quitar {igual.id} o elige otros escalones."
            )

    numeros = []
    for i, x in enumerate(e.escalones, 1):
        cuanto = None
        if x.gasto is not None:
            simbolo = alerts.SIMBOLOS.get(config.vs_currency, "")
            cuanto = f"{simbolo}{alerts._num(x.gasto)}"
        alerta = database.crear_puntual(
            config.database_path,
            coin_id,
            x.precio,
            False,
            config.vs_currency,
            None,
            escalera.nota_compra(i, len(e.escalones), cuanto),
        )
        numeros.append(alerta.id)
    logger.info("Escalera de compra de %s creada: %s", coin_id, numeros)
    return alerts.con_fuente(
        alerts.formatear_escalera_compra(e, numeros, config.vs_currency)
    )


def _stop_movil(
    config: Config, coin_id: str, porcentaje: float, valor: cartera.Valor
) -> str:
    # En la cartera manda lo que vale todo; en una cripto, su precio.
    ahora = valor.valor if coin_id == puntuales.CARTERA else valor.precio
    objetivo = stop.objetivo_movil(ahora, porcentaje)
    alerta = database.crear_puntual(
        config.database_path,
        coin_id,
        objetivo,
        False,
        config.vs_currency,
        None,
        stop.nota_movil(porcentaje),
    )
    database.guardar_movil(config.database_path, alerta.id, porcentaje)
    logger.info("Stop móvil %d creado: %s a %s", alerta.id, coin_id, objetivo)
    return alerts.con_fuente(
        alerts.formatear_stop_movil(
            coin_id, porcentaje, ahora, objetivo, alerta.id, config.vs_currency
        )
    )


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
