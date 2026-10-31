"""/ethereum: los años de Ethereum y lo que falta para su cumpleaños."""

from dataclasses import dataclass
from datetime import date

# El bloque 0 salió a media tarde en España, así que la fecha es la misma.
FECHA = date(2015, 7, 30)


@dataclass(frozen=True)
class Ethereum:
    hoy: date

    @property
    def dias(self) -> int:
        return (self.hoy - FECHA).days

    @property
    def años(self) -> int:
        este = FECHA.replace(year=self.hoy.year)
        return self.hoy.year - FECHA.year - (self.hoy < este)

    @property
    def faltan(self) -> int:
        """Días para el próximo 30 de julio. 0 si es hoy."""
        este = FECHA.replace(year=self.hoy.year)
        if este < self.hoy:
            este = este.replace(year=self.hoy.year + 1)
        return (este - self.hoy).days
