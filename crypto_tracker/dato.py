"""/dato: un dato curioso de cripto, al azar."""

import random

DATOS = (
    "El primer bloque de Bitcoin, del 3 de enero de 2009, lleva escrito un titular "
    "de The Times: «Chancellor on brink of second bailout for banks».",
    "La primera transacción de Bitcoin fue de Satoshi a Hal Finney: 10 BTC, "
    "el 12 de enero de 2009.",
    "El 22 de mayo de 2010 Laszlo Hanyecz pagó 10.000 BTC por dos pizzas. "
    "Por eso ese día es el Bitcoin Pizza Day.",
    "Nunca habrá más de 21 millones de bitcoin. El último se minará hacia el año 2140.",
    "Se calcula que Satoshi minó alrededor de un millón de bitcoin al principio. "
    "Nunca los ha movido.",
    "Nadie sabe quién es Satoshi Nakamoto. Su último mensaje en el foro fue en "
    "diciembre de 2010.",
    "El whitepaper de Bitcoin tiene solo 9 páginas.",
    "De media sale un bloque de Bitcoin cada 10 minutos, y cada 210.000 bloques "
    "(unos cuatro años) lo que se paga por minarlo baja a la mitad.",
    "HODL viene de una errata: en 2013 alguien escribió «I AM HODLING» en un foro "
    "mientras el precio se hundía, y se quedó.",
    "En 2013 James Howells tiró al vertedero un disco duro con unos 8.000 BTC. "
    "Lleva años intentando que le dejen buscarlo.",
    "El Salvador fue el primer país en hacer de Bitcoin moneda de curso legal, "
    "en septiembre de 2021.",
    "Vitalik Buterin propuso Ethereum en 2013, con 19 años.",
    "Con The Merge, en septiembre de 2022, Ethereum dejó la minería y gastó más "
    "de un 99% menos de energía.",
    "Dogecoin nació en 2013 como una broma, con el perro del meme de Shiba Inu.",
    "Mt. Gox llegó a mover cerca del 70% de las operaciones de bitcoin antes de "
    "quebrar en 2014.",
    "Un satoshi es la cien millonésima parte de un bitcoin: 0,00000001 BTC.",
)


def elegir(azar: random.Random | None = None) -> str:
    return (azar or random).choice(DATOS)
