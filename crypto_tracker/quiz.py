"""/quiz: una pregunta de cripto con tres respuestas para pulsar."""

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Pregunta:
    texto: str
    opciones: tuple[str, str, str]
    buena: int  # la posición de la correcta


PREGUNTAS = (
    Pregunta(
        "¿En qué año salió el primer bloque de Bitcoin?", ("2008", "2009", "2010"), 1
    ),
    Pregunta(
        "¿Cuántos bitcoin habrá como mucho?",
        ("21 millones", "100 millones", "No hay límite"),
        0,
    ),
    Pregunta(
        "¿Cuántos sats tiene un bitcoin?",
        ("Un millón", "Mil millones", "Cien millones"),
        2,
    ),
    Pregunta(
        "¿Qué compró Laszlo Hanyecz en 2010 con 10.000 BTC?",
        ("Un coche", "Dos pizzas", "Una casa"),
        1,
    ),
    Pregunta(
        "¿Quién propuso Ethereum?",
        ("Satoshi Nakamoto", "Elon Musk", "Vitalik Buterin"),
        2,
    ),
    Pregunta(
        "¿Cada cuántos bloques llega un halving?",
        ("21.000", "210.000", "2.100.000"),
        1,
    ),
    Pregunta(
        "¿Qué perro sale en Dogecoin?", ("Un Shiba Inu", "Un Chihuahua", "Un Husky"), 0
    ),
    Pregunta(
        "¿Qué país hizo primero de Bitcoin moneda de curso legal?",
        ("Argentina", "El Salvador", "Suiza"),
        1,
    ),
    Pregunta(
        "¿Cada cuánto sale de media un bloque de Bitcoin?",
        ("Cada minuto", "Cada hora", "Cada 10 minutos"),
        2,
    ),
    Pregunta(
        "¿Qué dejó atrás Ethereum con The Merge?",
        ("La minería", "Los contratos", "El ether"),
        0,
    ),
    Pregunta(
        "¿De dónde viene HODL?",
        ("Hold On for Dear Life", "Una errata en un foro", "Un exchange coreano"),
        1,
    ),
    Pregunta("¿Cuántas páginas tiene el whitepaper de Bitcoin?", ("9", "40", "120"), 0),
)


def sacar(azar: random.Random | None = None) -> int:
    return (azar or random).randrange(len(PREGUNTAS))


def interpretar(argumento: str) -> tuple[int, int] | None:
    """'3 1' (lo que lleva el botón) -> (pregunta, respuesta). Lo demás, None."""
    partes = argumento.split()
    if len(partes) != 2 or not all(p.isdigit() for p in partes):
        return None
    pregunta, respuesta = int(partes[0]), int(partes[1])
    if pregunta >= len(PREGUNTAS) or respuesta >= 3:
        return None
    return pregunta, respuesta
