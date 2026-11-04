"""/tarot: sacas una carta del tarot cripto, de broma."""

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Carta:
    nombre: str
    emoji: str
    significado: str


CARTAS = (
    Carta("La Ballena", "🐋", "Alguien muy grande va a mover el mercado. Tú no."),
    Carta("El Rug Pull", "🧶", "Esa moneda nueva tan prometedora... ya sabes."),
    Carta("El Halving", "✂️", "Lo bueno se hace esperar. Unos cuatro años."),
    Carta("La Vela Verde", "🟢", "Alegría pasajera. Haz captura antes de que se vaya."),
    Carta("La Vela Roja", "🔴", "Hoy no abras la app. Mañana tampoco."),
    Carta("El Minero", "⛏️", "El trabajo duro da frutos. Y facturas de la luz."),
    Carta("El Hodler", "💎", "Aguanta. Pase lo que pase, aguanta."),
    Carta("La Liquidación", "💥", "Has usado apalancamiento, ¿verdad? Lo sabía."),
    Carta("Satoshi", "🎭", "Las respuestas que buscas no van a aparecer. Él tampoco."),
    Carta("La Luna", "🌕", "Todos dicen que va a la luna. Todos dicen muchas cosas."),
    Carta("El Oso", "🐻", "Se acerca el invierno. Abrígate y no vendas."),
    Carta("El Toro", "🐂", "Viene una subida. O un toro de verdad. Corre."),
)


def sacar(azar: random.Random | None = None) -> Carta:
    return (azar or random).choice(CARTAS)
