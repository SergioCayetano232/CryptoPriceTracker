"""/tiempo: cómo va tu cartera hoy, como en el parte del tiempo."""

# Los mismos cortes que /emoji, para que la cara y el tiempo no se lleven la contraria.
PARTE = [
    (-10, "🌪️", "Huracán", "Agárrate a algo y no vendas en pleno temporal"),
    (-5, "⛈️", "Tormenta", "Mejor no abrir el exchange hasta que escampe"),
    (-2, "🌧️", "Lluvia", "Coge paraguas, que moja"),
    (-0.5, "🌦️", "Chubascos", "Algún chaparrón suelto, nada serio"),
    (0.5, "☁️", "Nublado", "Ni frío ni calor, día de no mirar"),
    (2, "🌤️", "Claros", "Va saliendo el sol"),
    (5, "☀️", "Soleado", "Buen día para mirar la cartera"),
    (10, "🔥", "Ola de calor", "Bebe agua y no hagas locuras"),
    (float("inf"), "🌋", "Erupción", "Esto quema, cuidado con el FOMO"),
]


def parte(cambio: float) -> tuple[str, str, str]:
    for hasta, emoji, cielo, consejo in PARTE:
        if cambio < hasta:
            return emoji, cielo, consejo
    return PARTE[-1][1:]
