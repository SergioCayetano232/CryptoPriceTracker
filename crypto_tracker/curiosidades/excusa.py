"""/excusa: una excusa al azar para cuando la cartera va mal."""

import random

EXCUSAS = (
    "Es culpa de la Fed. Siempre es culpa de la Fed.",
    "Las ballenas están sacudiendo a los débiles. Tú no eres débil.",
    "Es una corrección sana. Muy sana. Sanísima.",
    "No he perdido, es que todavía no he ganado.",
    "Ha salido un tuit de Elon y nadie lo vio venir.",
    "Lo de bajar es para coger impulso.",
    "Es lo que tiene comprar el día que más sube. Mala suerte.",
    "China lo ha prohibido otra vez. Van ya por la vigésima.",
    "Eso son los de los ETF haciendo cosas de ETF.",
    "Hoy es lunes. Los lunes no cuentan.",
    "Es la manipulación del mercado. La de hoy, en concreto.",
    "Estoy en el largo plazo. Esto es el corto plazo.",
    "Mi estrategia era otra, pero el mercado no la ha entendido.",
    "Es el ciclo de cuatro años. Estamos en el año malo.",
    "Lo tengo para mis nietos. Ellos verán.",
)


def elegir(azar: random.Random | None = None) -> str:
    return (azar or random).choice(EXCUSAS)
