"""/cumple: los años de Bitcoin y lo que falta para su cumpleaños."""

from dataclasses import dataclass
from datetime import date

# El bloque génesis. La primera versión del programa salió el 9 de enero,
# pero el cumpleaños que se celebra es este.
GENESIS = date(2009, 1, 3)


@dataclass(frozen=True)
class Cumple:
    hoy: date

    @property
    def dias(self) -> int:
        """Días que lleva funcionando."""
        return (self.hoy - GENESIS).days

    @property
    def años(self) -> int:
        este = GENESIS.replace(year=self.hoy.year)
        return self.hoy.year - GENESIS.year - (self.hoy < este)

    @property
    def faltan(self) -> int:
        """Días para el próximo 3 de enero. 0 si es hoy."""
        este = GENESIS.replace(year=self.hoy.year)
        if este < self.hoy:
            este = este.replace(year=self.hoy.year + 1)
        return (este - self.hoy).days
