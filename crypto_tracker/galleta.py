"""/galleta: la galleta de la suerte del día, de broma."""

import random
from dataclasses import dataclass
from datetime import date

FRASES = (
    "La paciencia es amarga, pero su fruto es verde.",
    "Pronto recibirás un airdrop. O un correo de phishing. Mira bien.",
    "El que vende con miedo, recompra con rabia.",
    "Un desconocido te hablará de una moneda con un perro. No le escuches.",
    "Tu próxima operación será un éxito si no la haces.",
    "Grandes cambios llegan a tu cartera. No dice hacia dónde.",
    "Quien guarda su semilla en un papel, duerme tranquilo.",
    "La suerte sonríe a los que no miran el precio cada cinco minutos.",
    "Hoy no es buen día para usar apalancamiento. Ningún día lo es.",
    "Lo que buscas está en tus claves privadas. No las pierdas.",
    "Esta galleta vale más que algunas memecoins.",
    "Comprarás en el mínimo. En el mínimo de la semana que viene.",
)


@dataclass(frozen=True)
class Galleta:
    frase: str
    numeros: list[int]  # de la suerte, sin repetir y de menor a mayor


def abrir(hoy: date) -> Galleta:
    # El día de semilla: en todo el día te sale la misma galleta.
    azar = random.Random(f"galleta-{hoy.isoformat()}")
    return Galleta(azar.choice(FRASES), sorted(azar.sample(range(1, 50), 6)))
