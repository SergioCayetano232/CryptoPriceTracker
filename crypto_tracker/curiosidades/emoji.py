"""/emoji: cómo va tu cartera hoy, en una cara."""

# Hasta qué cambio en 24 h vale cada cara. Entre -0,5 y 0,5 es no moverse.
CARAS = [
    (-10, "💀", "Mejor no mires"),
    (-5, "😱", "Día malo de verdad"),
    (-2, "😬", "Duele un poco"),
    (-0.5, "😕", "Bajando"),
    (0.5, "😐", "Ni fu ni fa"),
    (2, "🙂", "Subiendo"),
    (5, "😎", "Buen día"),
    (10, "🤑", "Día de los buenos"),
    (float("inf"), "🚀", "A la luna"),
]


def cambio(valores: list[tuple[float, float]]) -> float | None:
    """De (lo que vale ahora, su cambio en 24 h en %) al cambio de todo junto."""
    ahora = sum(v for v, _ in valores)
    # Lo que valía ayer cada una: el cambio va sobre ese precio, no sobre el de hoy.
    ayer = sum(v / (1 + c / 100) for v, c in valores)
    if not ayer:
        return None
    return (ahora / ayer - 1) * 100


def cara(cambio: float) -> tuple[str, str]:
    for hasta, emoji, frase in CARAS:
        if cambio < hasta:
            return emoji, frase
    return CARAS[-1][1:]
