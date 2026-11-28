"""Tu cartera en cafés, cañas, lambos... y otras cuentas de pasar el rato."""

import logging
from collections.abc import Callable
from datetime import date

from ..avisos import alerts
from ..curiosidades import ballena, emoji
from ..equivalencias import (
    aceite,
    airpods,
    alquiler,
    ave,
    bici,
    bigmac,
    boda,
    cafe,
    cana,
    carnet,
    churros,
    cine,
    coche,
    concierto,
    croquetas,
    equivale,
    futbol,
    gasolina,
    gimnasio,
    hotel,
    iphone,
    jamon,
    kebab,
    lambo,
    libro,
    loteria,
    luz,
    macbook,
    menu,
    metro,
    mundo,
    navidad,
    netflix,
    nochevieja,
    oro,
    paella,
    pan,
    peluqueria,
    piso,
    pizza,
    ps5,
    rolex,
    sofa,
    spotify,
    sueldo,
    supermercado,
    switch,
    taxi,
    tesla,
    tortilla,
    videojuego,
    vuelo,
    zapatillas,
)
from ..indicadores import millonario, sat
from ..inversion import cartera
from ..nucleo import botones, comandos, simbolos, telegram
from ..nucleo.config import Config
from .base import (
    SIN_CARTERA,
    Respuesta,
    _con_cambios,
    _consultar,
    _precio_o_pedirlo,
    _valor_guardado,
    _variacion,
)

logger = logging.getLogger("crypto_tracker")


def _comando_enletras(config: Config, argumento: str) -> Respuesta:
    valor = _valor_guardado(config)
    if isinstance(valor, str):
        return valor
    return alerts.formatear_enletras(valor, config.vs_currency)


def _comando_sat(config: Config, argumento: str) -> Respuesta:
    precio = _precio_o_pedirlo(config, "bitcoin")
    if isinstance(precio, str):
        return precio
    return alerts.formatear_sat(sat.Sat(precio), config.vs_currency)


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


def _equivale(config: Config, argumento: str) -> Respuesta:
    cosa = equivale.elegir(argumento)
    if cosa is None:
        return alerts.formatear_equivale(argumento)
    return COMANDOS[cosa](config, "")


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


COMANDOS: dict[str, Callable[[Config, str], Respuesta]] = {
    "pizza": lambda c, a: _pizza(c),
    "equivale": lambda c, a: _equivale(c, a),
    "mundo": lambda c, a: _mundo(c),
    "lambo": lambda c, a: _lambo(c),
    "enletras": _comando_enletras,
    "ballena": lambda c, a: _ballena(c),
    "cafe": lambda c, a: _cafe(c),
    "sueldo": lambda c, a: _sueldo(c),
    "gasolina": lambda c, a: _gasolina(c),
    "bigmac": lambda c, a: _bigmac(c),
    "iphone": lambda c, a: _iphone(c),
    "alquiler": lambda c, a: _alquiler(c),
    "oro": lambda c, a: _oro(c),
    "netflix": lambda c, a: _netflix(c),
    "ps5": lambda c, a: _ps5(c),
    "tesla": lambda c, a: _tesla(c),
    "spotify": lambda c, a: _spotify(c),
    "cana": lambda c, a: _cana(c),
    "switch": lambda c, a: _switch(c),
    "cine": lambda c, a: _cine(c),
    "gimnasio": lambda c, a: _gimnasio(c),
    "vuelo": lambda c, a: _vuelo(c),
    "super": lambda c, a: _super(c),
    "kebab": lambda c, a: _kebab(c),
    "metro": lambda c, a: _metro(c),
    "luz": lambda c, a: _luz(c),
    "libro": lambda c, a: _libro(c),
    "concierto": lambda c, a: _concierto(c),
    "airpods": lambda c, a: _airpods(c),
    "zapatillas": lambda c, a: _zapatillas(c),
    "ave": lambda c, a: _ave(c),
    "menu": lambda c, a: _menu(c),
    "hotel": lambda c, a: _hotel(c),
    "peluqueria": lambda c, a: _peluqueria(c),
    "macbook": lambda c, a: _macbook(c),
    "bici": lambda c, a: _bici(c),
    "churros": lambda c, a: _churros(c),
    "loteria": lambda c, a: _loteria(c),
    "piso": lambda c, a: _piso(c),
    "futbol": lambda c, a: _futbol(c),
    "taxi": lambda c, a: _taxi(c),
    "tortilla": lambda c, a: _tortilla(c),
    "videojuego": lambda c, a: _videojuego(c),
    "sofa": lambda c, a: _sofa(c),
    "coche": lambda c, a: _coche(c),
    "boda": lambda c, a: _boda(c),
    "jamon": lambda c, a: _jamon(c),
    "aceite": lambda c, a: _aceite(c),
    "paella": lambda c, a: _paella(c),
    "croquetas": lambda c, a: _croquetas(c),
    "pan": lambda c, a: _pan(c),
    "rolex": lambda c, a: _rolex(c),
    "emoji": lambda c, a: _emoji(c),
    "tiempo": lambda c, a: _tiempo(c),
    "carnet": lambda c, a: _carnet(c),
    "nochevieja": lambda c, a: _nochevieja(c),
    "navidad": lambda c, a: _navidad(c),
    "millonario": lambda c, a: _millonario(c, a),
    "sat": _comando_sat,
}
