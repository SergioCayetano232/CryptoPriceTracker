"""/ballena: qué bicho eres según los bitcoin que tienes."""

from dataclasses import dataclass

# Los tramos del meme de siempre, en BTC. Cada uno empieza donde acaba el anterior.
ANIMALES = (
    (0, "🦐", "gamba"),
    (1, "🦀", "cangrejo"),
    (10, "🐙", "pulpo"),
    (50, "🐟", "pez"),
    (100, "🐬", "delfín"),
    (500, "🦈", "tiburón"),
    (1000, "🐳", "ballena"),
    (5000, "🐋", "ballena jorobada"),
)


@dataclass(frozen=True)
class Ballena:
    btc: float  # los que tienes en la cartera

    @property
    def tramo(self) -> int:
        return max(i for i, (desde, _, _) in enumerate(ANIMALES) if self.btc >= desde)

    @property
    def animal(self) -> tuple[str, str]:
        _, emoji, nombre = ANIMALES[self.tramo]
        return emoji, nombre

    @property
    def siguiente(self) -> tuple[str, str] | None:
        if self.tramo + 1 == len(ANIMALES):
            return None
        _, emoji, nombre = ANIMALES[self.tramo + 1]
        return emoji, nombre

    @property
    def falta(self) -> float | None:
        """BTC que te faltan para el siguiente."""
        if self.siguiente is None:
            return None
        return ANIMALES[self.tramo + 1][0] - self.btc
