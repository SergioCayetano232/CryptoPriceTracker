"""Frases sueltas como "avísame si btc baja de 60000", pasadas al comando que toca.

Solo lo que se puede entender sin dudas. Nada que apunte compras o ventas: si
lo entendiera mal, te descuadraría la cartera.
"""

import re
import unicodedata

_CRIPTO = r"(?:(?:el|la|mi) )?(?P<cripto>[a-z0-9][a-z0-9-]*)"
_NUMERO = r"(?P<numero>\d[\d.,]*(?: ?(?:k|mil))?)(?: ?(?:€|eur|euros|\$|dolares))?"
_PCT = r"(?:un |el )?(?P<pct>\d[\d.,]*) ?(?:%|por ciento)"

_ALERTA = re.compile(
    rf"^(?:avisame|aviseme|avisa(?:me)?|dime) (?:si|cuando) {_CRIPTO} "
    r"(?:se )?(?P<verbo>baj[ae]|cae|caiga|sub[ae]|lleg(?:a|ue)|pas[ae]|super[ae]|este?)"
    rf"(?: (?:de|a|por|hasta|por encima de|por debajo de|los|las))* "
    rf"(?:{_PCT}|{_NUMERO})$"
)
_PRECIO = re.compile(
    r"^(?:(?:a )?cuanto (?:vale|esta|cuesta|va)|(?:que )?precio (?:de|tiene)|"
    rf"como (?:esta|va)) {_CRIPTO}(?: ahora)?$"
)
_CARTERA = re.compile(
    r"^(?:como (?:va|esta|voy con) mi cartera|cuanto vale mi cartera|mi cartera|"
    r"como voy|cuanto tengo)(?: hoy| ahora)?$"
)
_CALLAR = re.compile(
    r"^(?:callate|calla|silencio|no me avises)"
    r"(?: (?:durante |por )?(?P<cuanto>una|media|\d+) "
    r"(?P<unidad>horas?|minutos?|min|h))?$"
)
_AYUDA = re.compile(r"^(?:ayuda|que sabes hacer|que puedes hacer|que haces)$")

# "baja" y "baje": con "cuando" sale el subjuntivo, que es como se dice.
BAJA = ("baja", "baje", "cae", "caiga")
SUBE = ("sube", "suba")


def normalizar(texto: str) -> str:
    """Sin tildes, en minúscula y sin los signos de alrededor."""
    sin_tildes = "".join(
        c
        for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    sin_tildes = re.sub(r"[¿?¡!]", "", sin_tildes).strip().rstrip(".").strip()
    return re.sub(r"\s+", " ", sin_tildes)


def entender(texto: str) -> tuple[str, str] | None:
    """('alerta', 'btc 60000'), ('precio', 'eth')... None si no es una de estas."""
    frase = normalizar(texto)

    if m := _ALERTA.match(frase):
        cripto = m["cripto"]
        if m["pct"]:
            # "sube un 10%" es desde lo de ahora; "llega a un 10%" no se sabe.
            if m["verbo"] not in (*BAJA, *SUBE):
                return None
            signo = "-" if m["verbo"] in BAJA else "+"
            return "alerta", f"{cripto} {signo}{m['pct']}%"
        return "alerta", f"{cripto} {_numero(m['numero'])}"

    if m := _PRECIO.match(frase):
        if m["cripto"] == "cartera":
            return "cartera", ""
        return "precio", m["cripto"]

    if _CARTERA.match(frase):
        return "cartera", ""

    if m := _CALLAR.match(frase):
        if not m["cuanto"]:
            return "mute", ""
        return "mute", _duracion(m["cuanto"], m["unidad"])

    if _AYUDA.match(frase):
        return "ayuda", ""
    return None


def _numero(texto: str) -> str:
    """'60 mil' -> '60k', que es lo que entiende /alerta."""
    return re.sub(r" ?mil$", "k", texto).replace(" k", "k")


def _duracion(cuanto: str, unidad: str) -> str:
    """'una hora' -> '1h', 'media hora' -> '30m', '20 minutos' -> '20m'."""
    if cuanto == "media":
        return "30m"
    numero = "1" if cuanto == "una" else cuanto
    return f"{numero}{'h' if unidad.startswith('h') else 'm'}"
