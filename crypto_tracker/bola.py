"""/bola: la bola mágica contesta a lo que le preguntes, de broma."""

import random

RESPUESTAS = (
    "Sin ninguna duda.",
    "Sí, pero no se lo digas a nadie.",
    "Los astros dicen que sí. Tu cuenta corriente, que no.",
    "Ni de broma.",
    "Mejor no.",
    "Pregúntamelo después del halving.",
    "Ahora mismo no lo veo claro. Vuelve a agitarme.",
    "Todo apunta a que sí.",
    "Todo apunta a que no.",
    "Eso solo lo sabe Satoshi.",
    "Sí. Bueno, no. Bueno, haz lo que quieras.",
    "Con todo lo que llevas metido, ¿me lo preguntas a mí?",
    "Hodl y no preguntes más.",
    "Las ballenas ya lo han decidido por ti.",
)


class BolaError(Exception):
    """No le has preguntado nada."""


def interpretar(argumento: str) -> str:
    pregunta = argumento.strip()
    if not pregunta:
        raise BolaError("Pregúntame algo, como /bola ¿vendo ya?")
    return pregunta


def agitar(azar: random.Random | None = None) -> str:
    return (azar or random).choice(RESPUESTAS)
