"""/spotify: cuántos meses de Spotify te paga tu cartera."""

import math
from dataclasses import dataclass

# Premium Individual en España, desde la subida de 2025.
PRECIO = 11.99


@dataclass(frozen=True)
class Spotify:
    valor: float  # lo que vale tu cartera

    @property
    def meses(self) -> int:
        return math.floor(self.valor / PRECIO)
