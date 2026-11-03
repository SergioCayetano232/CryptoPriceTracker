"""/horoscopo: el horóscopo cripto de hoy para tu signo, de broma."""

import random
from dataclasses import dataclass
from datetime import date

SIGNOS = {
    "aries": "♈ Aries",
    "tauro": "♉ Tauro",
    "geminis": "♊ Géminis",
    "cancer": "♋ Cáncer",
    "leo": "♌ Leo",
    "virgo": "♍ Virgo",
    "libra": "♎ Libra",
    "escorpio": "♏ Escorpio",
    "sagitario": "♐ Sagitario",
    "capricornio": "♑ Capricornio",
    "acuario": "♒ Acuario",
    "piscis": "♓ Piscis",
}

# Con tilde o como se suele escribir, que nadie se aprende la lista.
OTROS_NOMBRES = {
    "géminis": "geminis",
    "cáncer": "cancer",
    "escorpión": "escorpio",
    "escorpion": "escorpio",
}

PREDICCIONES = (
    "Hoy los astros te piden que no mires el precio. Hazles caso.",
    "Mercurio está retrógrado y tu cartera también.",
    "Alguien de tu entorno te hablará de una moneda nueva. Huye.",
    "Buen día para aguantar. Malo para todo lo demás.",
    "Una vela verde se cruzará en tu camino. Disfrútala, dura poco.",
    "Los planetas se alinean a tu favor, pero el mercado no lee horóscopos.",
    "Hoy venderás justo antes de que suba. Es tu destino.",
    "La luna llena trae volatilidad. Y la nueva, también.",
    "Tu intuición te dirá que compres. Tu cuenta corriente, que no.",
    "Día perfecto para apuntar tus compras con /compra y no pensar más.",
    "Saturno te aconseja paciencia. Mucha. Años.",
    "El universo te prepara una sorpresa. Puede ser un airdrop o una estafa.",
)

CRIPTOS = ("Bitcoin", "Ethereum", "Solana", "Dogecoin", "Cardano", "XRP", "Litecoin")


class HoroscopoError(Exception):
    """El signo no existe."""


@dataclass(frozen=True)
class Horoscopo:
    signo: str  # el nombre bonito, con su símbolo
    prediccion: str
    cripto: str  # la de la suerte
    numero: int


def interpretar(argumento: str) -> str:
    texto = argumento.strip().lower()
    texto = OTROS_NOMBRES.get(texto, texto)
    if texto not in SIGNOS:
        raise HoroscopoError("¿De qué signo? Por ejemplo: /horoscopo aries")
    return texto


def leer(signo: str, hoy: date) -> Horoscopo:
    # Con el día y el signo de semilla: si lo pides dos veces hoy, te dice lo mismo.
    azar = random.Random(f"{hoy.isoformat()}-{signo}")
    return Horoscopo(
        SIGNOS[signo],
        azar.choice(PREDICCIONES),
        azar.choice(CRIPTOS),
        azar.randint(1, 99),
    )
