"""/equivale: los «cuántos X te da tu cartera» en un solo comando."""

import unicodedata

# Cada una es un comando de los de antes, que siguen funcionando sueltos.
COSAS = (
    "cafe", "cana", "kebab", "pan", "tortilla", "croquetas", "churros", "menu",
    "bigmac", "paella", "jamon", "aceite", "super", "gasolina", "luz", "metro",
    "taxi", "ave", "vuelo", "hotel", "cine", "concierto", "futbol", "libro",
    "netflix", "spotify", "gimnasio", "peluqueria", "loteria", "videojuego",
    "switch", "ps5", "airpods", "iphone", "macbook", "zapatillas", "bici",
    "sofa", "carnet", "boda", "rolex", "oro", "sueldo", "alquiler", "piso",
    "coche", "tesla", "lambo",
)  # fmt: skip

# Lo que la gente escribe y no sale solo quitando tildes y plurales.
OTROS_NOMBRES = {
    "cerveza": "cana",
    "cervezas": "cana",
    "big mac": "bigmac",
    "mac": "macbook",
    "lamborghini": "lambo",
    "supermercado": "super",
    "compra": "super",
    "abono": "metro",
    "avion": "vuelo",
    "pelo": "peluqueria",
    "gym": "gimnasio",
    "decimo": "loteria",
    "decimos": "loteria",
    "salario": "sueldo",
}


def _limpio(texto: str) -> str:
    sin = unicodedata.normalize("NFD", texto.strip().lower())
    return "".join(c for c in sin if unicodedata.category(c) != "Mn")


def elegir(texto: str) -> str | None:
    """'Cañas' -> 'cana'. None si no es ninguna."""
    limpio = _limpio(texto)
    if limpio in OTROS_NOMBRES:
        return OTROS_NOMBRES[limpio]
    # "iphones" o "kebabs": pruebo tal cual y luego sin el plural
    for nombre in (limpio, limpio.removesuffix("es"), limpio.removesuffix("s")):
        if nombre in COSAS:
            return nombre
    return None
