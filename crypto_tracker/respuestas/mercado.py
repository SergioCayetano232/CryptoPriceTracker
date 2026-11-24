"""Precios y mercado: lo que vale una cripto, el top, el miedo, la dominancia..."""

import logging
from datetime import date, datetime, timezone

from .. import (
    aleatoria,
    alerts,
    avisados,
    aviso_tendencias,
    binance,
    botones,
    cartera,
    coingecko,
    comandos,
    comisionred,
    convertir,
    database,
    dia,
    direccion,
    dominancia,
    funding,
    grafica,
    hoy,
    longshort,
    miedo,
    moneda,
    oi,
    redondo,
    simbolos,
    spread,
    telegram,
    top,
)
from ..config import Config
from ..mercado import Mercado
from ..precio import en_sats
from .base import (
    _con_cambios,
    _consultar,
    _direcciones_guardadas,
    _variacion,
)

logger = logging.getLogger("crypto_tracker")


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


def _tendencias(config: Config, argumento: str = "") -> str | comandos.ConBotones:
    try:
        avisar = aviso_tendencias.interpretar(argumento)
    except aviso_tendencias.AvisoError as e:
        return telegram.escape(str(e))
    if avisar is True:
        if database.aviso_tendencias(config.database_path) is None:
            database.guardar_aviso_tendencias(
                config.database_path, aviso_tendencias.Estado()
            )
        return (
            "🔥 Hecho. Si una de tu cartera o de las que vigilo entra en lo que más "
            "se busca, te aviso (lo miro cada 6 h y de cada una, una vez a la "
            "semana como mucho). Para quitarlo: /tendencias avisa no"
        )
    if avisar is False:
        database.guardar_aviso_tendencias(config.database_path, None)
        return "Hecho, ya no te aviso de las tendencias."

    try:
        lista = coingecko.tendencias_hoy(config.vs_currency)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"

    avisando = database.aviso_tendencias(config.database_path) is not None
    texto = alerts.formatear_tendencias(lista, avisando)
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


def _altseason(config: Config) -> str:
    try:
        temporada = coingecko.altseason_hoy()
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"
    if temporada is None:
        return "CoinGecko no me ha dado la lista ahora mismo. Prueba en un rato."
    mias = [w.coin_id for w in _con_cambios(config).watchlist]
    return alerts.con_fuente(alerts.formatear_altseason(temporada, mias))


def _mapa(config: Config) -> str | comandos.Foto:
    try:
        resultado = coingecko.mapa_hoy()
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"
    if resultado is None:
        return "CoinGecko no me ha dado la lista ahora mismo. Prueba en un rato."
    texto = alerts.con_fuente(alerts.formatear_mapa(resultado))
    mias = {w.coin_id for w in _con_cambios(config).watchlist}
    mias |= {p.coin_id for p in _con_cambios(config).cartera}
    try:
        png = grafica.dibujar_mapa(resultado, mias)
    except Exception as e:
        logger.warning("Mando /mapa sin imagen: %s", e)
        return texto
    return comandos.Foto(png, texto, texto)


def _sectores(config: Config) -> str | comandos.ConBotones:
    try:
        lista = coingecko.sectores_hoy()
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"
    if not lista:
        return "CoinGecko no me ha dado los sectores ahora mismo. Prueba en un rato."
    texto = alerts.con_fuente(alerts.formatear_sectores(lista))
    return comandos.ConBotones(texto, botones.actualizar("/sectores"))


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


def _comisionred(config: Config, argumento: str = "") -> str | comandos.ConBotones:
    try:
        orden = comisionred.interpretar(argumento)
    except comisionred.ComisionRedError as e:
        return telegram.escape(str(e))
    if orden == comisionred.QUITAR:
        if database.aviso_comisionred(config.database_path) is None:
            return f"No tenías ningún aviso puesto. Para ponerlo: {comisionred.EJEMPLO}"
        database.guardar_aviso_comisionred(config.database_path, None)
        return "Hecho, ya no te aviso de la comisión de la red."

    try:
        ahora, semana = comisionred.pedir()
    except comisionred.ComisionRedError as e:
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"

    datos = comisionred.leer(ahora, semana)
    if orden is not None:
        return _avisar_comisionred(config, datos, orden)

    precio = database.get_last_price(config.database_path, "bitcoin")
    if precio is None:
        precio = (_consultar(config, ["bitcoin"]) or {}).get("bitcoin")
    aviso = database.aviso_comisionred(config.database_path)
    texto = alerts.formatear_comisionred(datos, precio, config.vs_currency, aviso)
    if datos is None:
        return texto
    return comandos.ConBotones(texto, botones.actualizar("/comisionred"))


def _avisar_comisionred(
    config: Config, datos: comisionred.ComisionRed | None, limite: int
) -> str:
    if datos is None:
        return "mempool.space no me ha dado las comisiones. Prueba en un rato."
    ahora = comisionred.media_hora(datos.tarifas).sats_vb
    # Avisar de algo que ya pasa sería un mensaje nada más ponerlo.
    if comisionred.toca(datos, limite):
        return (
            f"Ya está a <b>{ahora} sat/vB</b>, no hace falta esperar. "
            "Míralo en /comisionred"
        )
    database.guardar_aviso_comisionred(config.database_path, limite)
    return (
        f"🔔 Hecho. Ahora está a {ahora} sat/vB: te aviso una vez cuando la de "
        f"media hora baje a <b>{limite}</b> o menos.\nPara quitarlo: /comisionred no"
    )


def _precios_de(
    config: Config, vigiladas: list[direccion.Vigilada]
) -> dict[str, float]:
    """El precio de cada cripto que sale en la lista: lo guardado y, si no, lo pido."""
    precios, faltan = {}, []
    for c in dict.fromkeys(direccion.coin_id(v.direccion) for v in vigiladas):
        precio = database.get_last_price(config.database_path, c)
        if precio is None:
            faltan.append(c)
        else:
            precios[c] = precio
    if faltan:
        precios.update(_consultar(config, faltan) or {})
    return precios


def _direccion(config: Config, argumento: str) -> str:
    try:
        que, cual, nombre = direccion.interpretar(argumento)
    except direccion.DireccionError as e:
        return telegram.escape(str(e))
    vigiladas = _direcciones_guardadas(config)

    if que == "quitar":
        v = direccion.buscar(vigiladas, cual)
        if v is None:
            return f"No vigilo ninguna que se llame <b>{telegram.escape(cual)}</b>."
        database.guardar_direccion(config.database_path, v.direccion, None)
        return f"Ya no vigilo <b>{telegram.escape(v.nombre)}</b>."

    if que == "ver":
        # Con lo de ahora y no lo guardado, por si el bot no está en --loop. No se
        # guarda: si se ha movido, el aviso del ciclo se perdería.
        al_dia = []
        for v in vigiladas:
            try:
                saldo = direccion.pedir(v.direccion)
                v = direccion.Vigilada(v.direccion, v.nombre, saldo.sats, v.txs)
            except direccion.DireccionError as e:
                logger.warning("No se pudo mirar %s: %s", v.direccion, e)
            al_dia.append(v)
        return alerts.formatear_direcciones(
            al_dia, _precios_de(config, al_dia), config.vs_currency
        )

    ya = direccion.buscar(vigiladas, cual)
    if ya is not None:
        return f"Ya la vigilo como <b>{telegram.escape(ya.nombre)}</b>."
    if direccion.buscar(vigiladas, nombre) is not None:
        return (
            f"Ya tienes una llamada <b>{telegram.escape(nombre)}</b>. "
            "Ponle otro nombre."
        )
    if len(vigiladas) >= direccion.MAXIMO:
        return f"Como mucho vigilo {direccion.MAXIMO}. Quita alguna antes."
    try:
        saldo = direccion.pedir(cual)
    except direccion.DireccionError as e:
        return f"No he podido mirarla: {telegram.escape(str(e))}"

    nueva = direccion.Vigilada(cual, nombre, saldo.sats, saldo.txs)
    database.guardar_direccion(config.database_path, cual, nueva.guardar())
    return alerts.formatear_direccion_nueva(
        nueva, _precios_de(config, [nueva]), config.vs_currency
    )


def _oi(config: Config, argumento: str) -> str:
    if len(argumento.split()) > 1:
        return f"De una en una. Por ejemplo: {oi.EJEMPLO}"
    if argumento:
        coin_id = simbolos.a_id(argumento)
    else:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {oi.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    par = funding.par(coin_id, argumento)
    try:
        datos = oi.pedir(par)
    except funding.FundingError as e:
        if str(e) == "sin futuros":
            return (
                f"<b>{telegram.escape(coin_id)}</b> no tiene futuros en Binance. "
                "Prueba con su símbolo, como /oi btc"
            )
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"
    resultado = oi.leer(par, datos)
    if resultado is None:
        return "Binance no me ha dado lo apostado. Prueba en un rato."
    return alerts.formatear_oi(resultado, coin_id)


def _longshort(config: Config, argumento: str) -> str:
    if len(argumento.split()) > 1:
        return f"De una en una. Por ejemplo: {longshort.EJEMPLO}"
    if argumento:
        coin_id = simbolos.a_id(argumento)
    else:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return f"¿De cuál? Por ejemplo: {longshort.EJEMPLO}"
        coin_id = vigiladas[0].coin_id

    par = funding.par(coin_id, argumento)
    try:
        todos, grandes = longshort.pedir(par)
    except funding.FundingError as e:
        if str(e) == "sin futuros":
            return (
                f"<b>{telegram.escape(coin_id)}</b> no tiene futuros en Binance. "
                "Prueba con su símbolo, como /longshort btc"
            )
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"
    resultado = longshort.leer(par, todos, grandes)
    if resultado is None:
        return "Binance no me ha dado cuántos apuestan a cada lado. Prueba en un rato."
    return alerts.formatear_longshort(resultado, coin_id)


def _funding(config: Config, argumento: str) -> str | comandos.ConBotones:
    argumento, orden = funding.separar(argumento)
    if len(argumento.split()) > 1:
        return "De una en una. Por ejemplo: /funding btc"
    if argumento:
        coin_id = simbolos.a_id(argumento)
    else:
        vigiladas = _con_cambios(config).watchlist
        if not vigiladas:
            return "¿De cuál? Por ejemplo: /funding btc"
        coin_id = vigiladas[0].coin_id

    par = funding.par(coin_id, argumento)
    if orden == funding.QUITAR:
        if database.quitar_funding(config.database_path, par):
            return f"Hecho, ya no te aviso del funding de {telegram.escape(coin_id)}."
        return f"No tenías ese aviso. Para ponerlo: {funding.EJEMPLO_AVISO}"
    try:
        ahora, antes = funding.pedir(par)
    except funding.FundingError as e:
        if str(e) == "sin futuros":
            return (
                f"<b>{telegram.escape(coin_id)}</b> no tiene futuros en Binance. "
                "Prueba con su símbolo, como /funding btc"
            )
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"

    resultado = funding.leer(par, ahora, antes)
    if resultado is None:
        return "Binance no me ha dado el funding. Prueba en un rato."
    if orden == funding.AVISA:
        # Si ya está en una punta lo apunto: avisar de lo que acabas de ver sobra.
        database.guardar_funding(
            config.database_path,
            funding.Vigilado(
                par, coin_id, funding.extremo(resultado), datetime.now(timezone.utc)
            ),
        )
        return (
            f"🔔 Hecho: te aviso cuando el funding de <b>{telegram.escape(coin_id)}"
            "</b> se vaya a un extremo, muy apalancado al alza o muchos apostando "
            f"a que baja. Ahora: {resultado.emoji} {resultado.nivel.lower()}.\n"
            f"Para quitarlo: /funding {telegram.escape(coin_id)} no"
        )
    avisa = any(v.par == par for v in database.get_funding(config.database_path))
    return comandos.ConBotones(
        alerts.formatear_funding(resultado, avisa),
        botones.actualizar(f"/funding {coin_id}"),
    )


def _spread(config: Config, argumento: str) -> str | comandos.ConBotones:
    try:
        coin_ids = spread.interpretar(argumento)
    except spread.SpreadError as e:
        return telegram.escape(str(e))
    if not coin_ids:
        vigiladas = _con_cambios(config).watchlist
        coin_ids = [w.coin_id for w in vigiladas][: simbolos.MAX_VARIAS]
    if not coin_ids:
        return f"¿De cuáles? Por ejemplo: {spread.EJEMPLO}"
    if config.vs_currency not in binance.MONEDAS:
        return "Binance solo me da precios en euros o en dólares."

    # Los dos de ahora y no lo guardado: si no, la diferencia sería de minutos.
    try:
        de_coingecko = coingecko.get_prices(coin_ids, config.vs_currency)
    except coingecko.CoinGeckoError as e:
        return f"CoinGecko no contesta ahora mismo: {telegram.escape(str(e))}"
    try:
        de_binance = binance.precios(coin_ids, config.vs_currency)
    except binance.BinanceError as e:
        return f"Binance no contesta ahora mismo: {telegram.escape(str(e))}"

    filas, sueltas = spread.calcular(coin_ids, de_coingecko, de_binance)
    if not filas:
        return "No he podido comparar ninguna. " + "; ".join(
            f"{c}: {spread.por_que_no(c)}" for c in sueltas
        )
    texto = alerts.con_fuente(spread.texto(filas, sueltas, config.vs_currency))
    # Con lo que escribiste y no con los ids, que «avalanche-2» ocupa mucho.
    orden = f"/spread {argumento}".strip()
    if len(orden.encode()) > botones.MAX_DATOS:
        return texto
    return comandos.ConBotones(texto, botones.actualizar(orden))


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


def _dominancia(config: Config) -> str:
    try:
        datos = coingecko.mercado_global(config.vs_currency)
    except coingecko.CoinGeckoError as e:
        return f"No he podido mirarlo ahora mismo: {telegram.escape(str(e))}"
    if datos.bitcoin is None:
        return "CoinGecko no ha dicho qué parte es de bitcoin. Prueba en un rato."

    ahora = datetime.now(timezone.utc)
    fotos = database.get_dominancia(_del_mercado(config), dominancia.HORAS)
    resultado = dominancia.calcular(datos, fotos, ahora)
    # Ya que se ha consultado, que sirva de foto de hoy si no la había.
    _guardar_foto(config, datos, ahora)
    return alerts.con_fuente(alerts.formatear_dominancia(resultado))


def foto_dominancia(config: Config) -> None:
    """Una vez al día apunta qué parte del mercado es bitcoin. Gasta una consulta."""
    ahora = datetime.now(timezone.utc)
    try:
        if not dominancia.toca_guardar(
            database.ultima_dominancia(config.database_path), ahora
        ):
            return
        datos = coingecko.mercado_global(config.vs_currency)
    except (database.DatabaseError, coingecko.CoinGeckoError) as e:
        # Si falla, lo intenta el siguiente ciclo: no es un aviso, no corre prisa.
        logger.warning("No se pudo apuntar la dominancia: %s", e)
        return
    if datos.bitcoin is not None:
        _guardar_foto(config, datos, ahora)


def _del_mercado(config: Config) -> str:
    """Es del mercado, igual para todos: lo de un invitado va en tu archivo."""
    return config.archivo_dueño or config.database_path


def _guardar_foto(config: Config, datos: Mercado, ahora: datetime) -> None:
    try:
        ultima = database.ultima_dominancia(_del_mercado(config))
        if dominancia.toca_guardar(ultima, ahora):
            database.guardar_dominancia(
                _del_mercado(config),
                dominancia.Foto(ahora, datos.bitcoin, datos.ethereum, datos.estables),
            )
    except database.DatabaseError as e:
        logger.warning("No se pudo apuntar la dominancia: %s", e)


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
