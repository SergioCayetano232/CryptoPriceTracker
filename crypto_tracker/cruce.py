"""Aviso de cuando la media de 50 días cruza la de 200: cruz dorada o de la muerte."""

from dataclasses import dataclass
from datetime import date

CORTA = 50
LARGA = 200
# Unos días de más por si falta alguno suelto.
HORAS = (LARGA + 10) * 24

ARRIBA = "arriba"
ABAJO = "abajo"

# Con las dos casi iguales, el precio de hoy las haría cruzarse y descruzarse en
# el mismo día. Hasta que no se separan esto, se queda como estaba.
MARGEN = 0.5


@dataclass(frozen=True)
class Cruce:
    coin_id: str
    corta: float
    larga: float
    ahora: float

    @property
    def diferencia(self) -> float:
        """Cuánto está la corta por encima de la larga, en %."""
        return (self.corta / self.larga - 1) * 100

    @property
    def lado(self) -> str | None:
        """Dónde está la corta. None si van tan juntas que no se sabe."""
        if self.diferencia >= MARGEN:
            return ARRIBA
        return ABAJO if self.diferencia <= -MARGEN else None


def calcular(
    coin_id: str, dias: list[tuple[date, float]], ahora: float
) -> Cruce | None:
    """None si no hay días bastantes para la de 200."""
    # Aquí y no arriba: config usa LARGA, y media acaba importando config.
    from . import media

    corta = media.calcular(dias, CORTA)
    larga = media.calcular(dias, LARGA)
    if corta is None or larga is None:
        return None
    return Cruce(coin_id, corta, larga, ahora)


def toca(c: Cruce, avisado: str | None) -> bool:
    # La primera vez solo se apunta dónde está: eso no es un cruce, es que miro.
    return avisado is not None and c.lado is not None and c.lado != avisado


def apuntar(c: Cruce, avisado: str | None) -> str | None:
    """Lo que se queda guardado: dónde está ahora, o lo de antes si no está claro."""
    return c.lado or avisado
