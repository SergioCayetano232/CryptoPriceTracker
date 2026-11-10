"""/enletras: lo que vale tu cartera, escrito como en un cheque."""

UNIDADES = [
    "cero",
    "uno",
    "dos",
    "tres",
    "cuatro",
    "cinco",
    "seis",
    "siete",
    "ocho",
    "nueve",
    "diez",
    "once",
    "doce",
    "trece",
    "catorce",
    "quince",
    "dieciséis",
    "diecisiete",
    "dieciocho",
    "diecinueve",
    "veinte",
    "veintiuno",
    "veintidós",
    "veintitrés",
    "veinticuatro",
    "veinticinco",
    "veintiséis",
    "veintisiete",
    "veintiocho",
    "veintinueve",
]
DECENAS = [
    "_",
    "_",
    "_",
    "treinta",
    "cuarenta",
    "cincuenta",
    "sesenta",
    "setenta",
    "ochenta",
    "noventa",
]
CENTENAS = [
    "_",
    "ciento",
    "doscientos",
    "trescientos",
    "cuatrocientos",
    "quinientos",
    "seiscientos",
    "setecientos",
    "ochocientos",
    "novecientos",
]

# Las libras no, que son femenino y saldría "un libra".
MONEDAS = {"eur": "euros", "usd": "dólares"}


def _menos_de_mil(n: int) -> str:
    if n == 100:
        return "cien"
    centenas, resto = divmod(n, 100)
    partes = [CENTENAS[centenas]] if centenas else []
    if resto < 30:
        if resto or not centenas:
            partes.append(UNIDADES[resto])
    else:
        decenas, unidad = divmod(resto, 10)
        partes.append(DECENAS[decenas] + (f" y {UNIDADES[unidad]}" if unidad else ""))
    return " ".join(partes)


def _apocope(texto: str) -> str:
    """Delante de mil, millones o euros: 'uno' se queda en 'un'."""
    if texto.endswith("veintiuno"):
        return texto.removesuffix("veintiuno") + "veintiún"
    if texto.endswith("uno"):
        return texto[:-1]
    return texto


def letras(n: int) -> str:
    """El entero en palabras, ya con 'un' en vez de 'uno' al final."""
    millones, resto = divmod(n, 1_000_000)
    miles, unidades = divmod(resto, 1000)
    partes = []
    if millones == 1:
        partes.append("un millón")
    elif millones:
        partes.append(f"{letras(millones)} millones")
    if miles == 1:
        partes.append("mil")
    elif miles:
        partes.append(f"{_apocope(_menos_de_mil(miles))} mil")
    if unidades or not partes:
        partes.append(_apocope(_menos_de_mil(unidades)))
    return " ".join(partes)


def dinero(valor: float, currency: str) -> str:
    """1234.5 -> 'Mil doscientos treinta y cuatro euros con cincuenta céntimos'."""
    centimos = round(valor * 100)
    enteros, centimos = divmod(centimos, 100)
    moneda = MONEDAS.get(currency.lower(), currency.upper())
    if enteros == 1 and moneda in MONEDAS.values():
        moneda = moneda.removesuffix("es").removesuffix("s")
    # Con millones justos va con 'de': un millón de euros.
    de = "de " if enteros and enteros % 1_000_000 == 0 else ""
    texto = f"{letras(enteros)} {de}{moneda}"
    if centimos:
        texto += f" con {letras(centimos)} céntimo{'s' if centimos > 1 else ''}"
    return texto[0].upper() + texto[1:]
