"""Lo que contesta sobre tu cartera: compras, ventas, Hacienda y cómo te va."""

import logging
from dataclasses import replace
from datetime import date, datetime, timezone

from .. import (
    alerts,
    apodo,
    apy,
    arrepentido,
    botones,
    cartera,
    coingecko,
    comandos,
    comision,
    comisiones,
    compensar,
    compras,
    corregir,
    database,
    deposito,
    doble,
    emocion,
    equilibrio,
    fantasma,
    fifo,
    ganancias,
    grafica,
    herencia,
    hodl,
    impuestos,
    inflacion,
    limite,
    meta,
    miedo,
    mitad,
    modelo721,
    moneda,
    movimientos,
    nota,
    objetivo,
    pelotazo,
    periodo,
    permuta,
    plan,
    posicion,
    primera,
    promediar,
    rebalanceo,
    record,
    renta,
    rentabilidad,
    reparto,
    riesgo,
    sesgo,
    simbolos,
    sivendo,
    tarjeta,
    telegram,
    timing,
    volatilidad,
    vsbolsa,
    vsbtc,
)
from ..config import Config
from .base import (
    SIN_CARTERA,
    _con_cambios,
    _consultar,
    _precio_o_pedirlo,
    _precios_guardados,
    _valor_guardado,
)

logger = logging.getLogger("crypto_tracker")

# Una cartera se mira a mas largo plazo que un precio suelto.
HORAS_CARTERA = 7 * 24


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
        config.database_path,
        coin_id,
        "compra",
        cantidad,
        coste,
        antes,
        ahora,
        apunte,
        pagada,
    )
    logger.info("Cartera: compra %s de %s por %s", cantidad, coin_id, coste)
    texto = alerts.formatear_compra(
        cantidad,
        coste,
        ahora,
        config.vs_currency,
        antes,
        precio,
        pagada,
        apunte,
    )
    # La compra ya está apuntada: si esto falla, mejor sin aviso que sin respuesta.
    try:
        actual = _limite_del_mes(config)
    except database.DatabaseError as e:
        logger.warning("No se pudo mirar el límite de compras: %s", e)
        actual = None
    if actual and (linea := alerts.linea_limite(actual, config.vs_currency)):
        texto += "\n\n" + linea
    return comandos.ConBotones(
        texto, botones.deshacer_movimiento(numero) + botones.emociones(numero)
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
        config.database_path,
        coin_id,
        "venta",
        vendido,
        cobrado,
        antes,
        queda,
        apunte,
        pagada,
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
        botones.deshacer_movimiento(numero) + botones.emociones(numero),
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


def _impuestos(config: Config, argumento: str) -> str | comandos.Archivo:
    argumento, csv = renta.pide_csv(argumento)
    try:
        año = impuestos.interpretar(argumento, date.today().year)
    except impuestos.ImpuestosError as e:
        return telegram.escape(str(e))
    todos = database.get_movimientos(config.database_path, None)
    if csv:
        return _renta(config, todos, año)
    return alerts.formatear_impuestos(
        impuestos.calcular(todos, año),
        config.vs_currency,
        impuestos.recompensas_de(todos, año),
    )


def _renta(
    config: Config, todos: list[movimientos.Movimiento], año: int
) -> str | comandos.Archivo:
    ventas = renta.ventas(todos, año)
    if not ventas:
        return f"En {año} no has vendido nada, así que no hay nada que declarar."
    cuantas = "1 venta" if len(ventas) == 1 else f"{len(ventas)} ventas"
    pie = [
        f"🏛️ {cuantas} de {año}, con FIFO como Hacienda",
        "<i>Para la Renta, en ganancias por transmisión de monedas virtuales. "
        "Las comisiones ya van dentro. Es orientativo.</i>",
    ]
    if any(v.ganancia is None for v in ventas):
        pie.append("<i>Las que no tienen precio van sin cifras y fuera del total.</i>")
    if config.vs_currency.lower() != "eur":
        pie.append(
            f"<i>Ojo: va en {config.vs_currency.upper()}, "
            "y Hacienda lo quiere en euros.</i>"
        )
    return comandos.Archivo(
        renta.a_csv(ventas, config.vs_currency),
        renta.nombre(año),
        "\n".join(pie),
        "No he podido mandarte el archivo. Prueba en un rato.",
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


def _permuta(config: Config, argumento: str) -> str:
    try:
        origen, destino, cantidad, texto_comision = permuta.interpretar(argumento)
        antes = movimientos.buscar(_con_cambios(config).cartera, origen)
        queda = movimientos.vender(antes, origen, cantidad)
    except movimientos.MovimientoError as e:
        return telegram.escape(str(e))

    vendido = antes.cantidad if cantidad is None else cantidad
    precio_origen = _precio_o_pedirlo(config, origen)
    if isinstance(precio_origen, str):
        return precio_origen
    precio_destino = _precio_o_pedirlo(config, destino)
    if isinstance(precio_destino, str):
        return precio_destino

    todos = database.get_movimientos(config.database_path, None)
    este_año = impuestos.calcular(todos, date.today().year)
    historia = [m for m in todos if m.coin_id == origen]
    try:
        resultado = permuta.calcular(
            antes,
            vendido,
            precio_origen,
            destino,
            precio_destino,
            queda,
            este_año,
            historia,
            texto_comision,
        )
    except movimientos.MovimientoError as e:
        return telegram.escape(str(e))
    return alerts.formatear_permuta(resultado, config.vs_currency)


def _modelo721(config: Config) -> str:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    hoy = date.today()
    cierre = None
    if modelo721.en_plazo(hoy):
        cierre = _valor_cierre(config, hoy.year - 1)
    return alerts.formatear_modelo721(
        modelo721.calcular(valor, cierre, hoy), config.vs_currency, hoy
    )


def _valor_cierre(config: Config, año: int) -> float | None:
    """Lo que valía la cartera el 31 de diciembre, con los precios guardados."""
    fin = modelo721.cierre(año)
    todos = database.get_movimientos(config.database_path, None)
    posiciones = modelo721.cartera_en(list(_con_cambios(config).cartera), todos, fin)
    if not posiciones:
        return 0.0
    horas = modelo721.horas_desde(fin, datetime.now(timezone.utc))
    precios = {}
    for p in posiciones:
        precio = database.get_price_at(config.database_path, p.coin_id, horas)
        if precio:
            precios[p.coin_id] = precio
    return cartera.valor_total(posiciones, precios)


def _compensar(config: Config) -> str:
    hoy = date.today()
    plan = _plan_compensar(config, hoy)
    if isinstance(plan, str):
        return plan
    return alerts.formatear_compensar(plan, config.vs_currency, hoy)


def _plan_compensar(config: Config, hoy: date) -> compensar.Compensacion | str:
    """Lo de /compensar sin el texto. Un str es que no se pudo."""
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

    return compensar.calcular(este_año, fifo.lotes(todos, cartera), precios)


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


def _comisiones(config: Config, argumento: str) -> str:
    try:
        año = comisiones.interpretar(argumento, date.today().year)
    except comisiones.ComisionesError as e:
        return telegram.escape(str(e))
    todos = database.get_movimientos(config.database_path, None)
    return alerts.formatear_comisiones(
        comisiones.calcular(todos, año), config.vs_currency, año
    )


def _inflacion(config: Config) -> str:
    todos = database.get_movimientos(config.database_path, None)
    if not any(m.tipo == "compra" for m in todos):
        return (
            "No has apuntado ninguna compra por aquí, y lo del PORTFOLIO del .env "
            f"no lleva fecha. Apúntalas así: {movimientos.EJEMPLO_COMPRA}"
        )
    dentro, tienes = rentabilidad.contables(todos)
    if not dentro:
        return (
            "Tus compras no llevan lo que costaron, así que no puedo compararlas. "
            f"La próxima, con precio: {movimientos.EJEMPLO_COMPRA}"
        )
    try:
        ipc = inflacion.pedir()
    except inflacion.InflacionError as e:
        return f"No he podido mirar el IPC: {telegram.escape(str(e))}"
    precios = _consultar(config, list(tienes)) if tienes else {}
    if precios is None:
        return "No he podido consultar los precios. Prueba en un rato."
    resultado = inflacion.calcular(todos, precios, datetime.now(timezone.utc), ipc)
    if resultado is None:
        return "No he podido consultar los precios. Prueba en un rato."
    return alerts.formatear_inflacion(resultado, config.vs_currency)


def _deposito(config: Config, argumento: str) -> str:
    try:
        tipo = deposito.interpretar(argumento)
    except deposito.DepositoError as e:
        return telegram.escape(str(e))
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
    resultado = deposito.calcular(todos, precios, datetime.now(timezone.utc), tipo)
    if resultado is None:
        if not rentabilidad.contables(todos)[0]:
            return (
                "Tus compras no llevan lo que costaron, así que no puedo compararlas. "
                f"La próxima, con precio: {movimientos.EJEMPLO_COMPRA}"
            )
        return "No he podido consultar los precios. Prueba en un rato."
    return alerts.formatear_deposito(resultado, config.vs_currency)


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


def _timing(config: Config, argumento: str) -> str:
    coin_id = simbolos.a_id(argumento) if argumento else None
    todos = database.get_movimientos(config.database_path, None, coin_id)
    compras_ = timing.a_mirar(todos)
    if not compras_:
        de = f" de <b>{telegram.escape(coin_id)}</b>" if coin_id else ""
        return (
            f"No has apuntado ninguna compra{de} por aquí. Lo del PORTFOLIO del .env "
            f"no lleva fecha. Apúntala así: {movimientos.EJEMPLO_COMPRA}"
        )

    # Una consulta por cripto: lo guardado no llega a las compras de hace meses.
    dias = timing.dias_a_pedir(compras_, datetime.now(timezone.utc).date())
    series = {}
    for cid in dict.fromkeys(m.coin_id for m in compras_):
        try:
            series[cid] = coingecko.historico(cid, dias, config.vs_currency)
        except coingecko.CoinGeckoError as e:
            logger.warning("/timing sin precios de %s: %s", cid, e)

    resultado = timing.calcular(compras_, series)
    if resultado is None:
        return (
            "No puedo comparar ninguna compra: o no llevan lo que costaron, o son de "
            "hace más de un año y CoinGecko no me da precios de entonces"
        )
    return alerts.con_fuente(
        alerts.formatear_timing(resultado, config.vs_currency, coin_id)
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


def _vsbolsa(config: Config, argumento: str) -> str:
    try:
        indice = vsbolsa.interpretar(argumento, config.vs_currency)
    except vsbolsa.BolsaError as e:
        return telegram.escape(str(e))
    todos = database.get_movimientos(config.database_path, None)
    if not todos:
        return (
            "No has apuntado ninguna compra por aquí, y lo del PORTFOLIO del .env "
            f"no lleva fecha. Apúntalas así: {movimientos.EJEMPLO_COMPRA}"
        )
    precios = _consultar(config, list({m.coin_id for m in todos}))
    if precios is None:
        return "No he podido consultar los precios. Prueba en un rato."

    # Unos días antes, por si la primera compra fue en fin de semana.
    desde = min(m.cuando for m in todos) - vsbolsa.MARGEN
    try:
        serie, ahora = vsbolsa.pedir(indice[1], desde)
    except vsbolsa.BolsaError as e:
        return f"No he podido mirar la bolsa: {telegram.escape(str(e))}"

    resultado = vsbolsa.calcular(todos, serie, ahora, precios, indice)
    if resultado is None:
        return (
            "No tengo nada que comparar: tus compras no llevan precio, o no "
            "he podido consultar el de alguna de hoy."
        )
    return alerts.formatear_vsbolsa(resultado, config.vs_currency)


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


def _limite(config: Config, argumento: str) -> str:
    try:
        que, cifra = limite.interpretar(argumento)
    except limite.LimiteError as e:
        return telegram.escape(str(e))

    if que == limite.QUITAR:
        database.guardar_limite_compras(config.database_path, None)
        return "Hecho, ya no tienes límite de compras."
    if que == limite.PONER:
        database.guardar_limite_compras(config.database_path, cifra)

    actual = _limite_del_mes(config)
    if actual is None:
        return f"No tienes límite de compras. Ponlo con {limite.EJEMPLO}"
    return alerts.formatear_limite(
        actual, config.vs_currency, date.today(), puesto=que == limite.PONER
    )


def _limite_del_mes(config: Config) -> limite.Limite | None:
    """El límite y lo comprado este mes. None si no hay límite."""
    tope = database.limite_compras(config.database_path)
    if tope is None:
        return None
    todos = database.get_movimientos(config.database_path, limite=None)
    return limite.Limite(tope, limite.gastado(todos, date.today()))


def _apy(config: Config, argumento: str) -> str:
    try:
        peticion = apy.interpretar(argumento)
    except apy.ApyError as e:
        return telegram.escape(str(e))

    coin_id, cantidad = peticion.coin_id, peticion.cantidad
    if cantidad is None:
        tienes = [p for p in _con_cambios(config).cartera if p.coin_id == coin_id]
        if not tienes or not tienes[0].cantidad:
            return (
                f"No tienes <b>{telegram.escape(coin_id)}</b> en la cartera. "
                "Dime cuánta: /apy 2 eth 4%"
            )
        cantidad = tienes[0].cantidad

    precio = _precio_o_pedirlo(config, coin_id)
    if isinstance(precio, str):
        return precio
    unidad = simbolos.de_id(coin_id) or coin_id.replace("-", " ").title()
    tramos = apy.calcular(cantidad, peticion.apy, peticion.años)
    return alerts.formatear_apy(
        unidad,
        cantidad,
        peticion.apy,
        tramos,
        precio,
        config.vs_currency,
        de_cartera=peticion.cantidad is None,
    )


def _plan(config: Config, argumento: str) -> str:
    try:
        peticion = plan.interpretar(argumento)
    except plan.PlanError as e:
        return telegram.escape(str(e))

    # Sin cartera se empieza de cero, que también es un plan.
    inicio = 0.0
    if _con_cambios(config).cartera:
        valor = _valor_guardado(config)
        if isinstance(valor, str):
            return valor
        inicio = valor
    camino = plan.calcular(peticion, inicio)
    return alerts.formatear_plan(camino, config.vs_currency, date.today())


def _posicion(config: Config, argumento: str) -> str:
    try:
        peticion = posicion.interpretar(argumento)
    except posicion.PosicionError as e:
        return telegram.escape(str(e))

    # Sin cripto son solo cuentas: no hace falta gastar una consulta.
    precio = None
    if peticion.coin_id:
        precios = _consultar(config, [peticion.coin_id])
        precio = (precios or {}).get(peticion.coin_id)
        if precio is None:
            return "No he podido consultar los precios. Prueba en un rato."

    try:
        entrada = posicion.calcular(peticion, precio)
    except posicion.PosicionError as e:
        return telegram.escape(str(e))
    texto = alerts.formatear_posicion(entrada, config.vs_currency)
    return alerts.con_fuente(texto) if precio else texto


def _valor_cartera(config: Config) -> float | None:
    posiciones = list(_con_cambios(config).cartera)
    precios = coingecko.get_prices([p.coin_id for p in posiciones], config.vs_currency)
    return cartera.valor_total(posiciones, precios)


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


def _tarjeta(config: Config, argumento: str) -> str | comandos.Foto:
    try:
        horas = tarjeta.interpretar(argumento)
    except periodo.PeriodoError as e:
        return telegram.escape(str(e))
    posiciones = list(_con_cambios(config).cartera)
    if not posiciones:
        return SIN_CARTERA
    precios = _precios_guardados(config, posiciones)
    valores, faltan = cartera.valorar(posiciones, precios)
    # Sin una, los % de las demás saldrían inflados.
    if faltan:
        return "Ahora mismo no tengo el precio de todo. Prueba en un rato."

    filas = database.get_series(
        config.database_path, [p.coin_id for p in posiciones], horas, config.vs_currency
    )
    resultado = tarjeta.calcular(
        valores, cartera.serie_valor(posiciones, filas), horas, date.today()
    )
    if resultado is None:
        return "Tu cartera ahora mismo no vale nada, no hay nada que enseñar."
    if resultado.total is None and resultado.tramo is None:
        return (
            "Aún no tengo con qué hacerla: apunta lo que te costó cada una con "
            f"/compra o espera a que guarde precios ({periodo.nombre(horas)})."
        )
    texto = alerts.formatear_tarjeta(resultado)
    try:
        png = grafica.dibujar_tarjeta(resultado)
    except Exception as e:
        logger.warning("Mando /tarjeta sin imagen: %s", e)
        return texto
    return comandos.Foto(png, texto, texto)


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
