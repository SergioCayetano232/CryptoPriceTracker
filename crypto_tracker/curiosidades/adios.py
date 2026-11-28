"""/adios: el tiempo que lleva Satoshi sin aparecer desde su último mensaje."""

from dataclasses import dataclass
from datetime import date

# Su último mensaje en el foro de bitcointalk. Luego mandó algún correo
# privado, pero esa es la última vez que habló en público.
FECHA = date(2010, 12, 12)


@dataclass(frozen=True)
class Adios:
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
        """Días para el próximo 12 de diciembre. 0 si es hoy."""
        este = FECHA.replace(year=self.hoy.year)
        if este < self.hoy:
            este = este.replace(year=self.hoy.year + 1)
        return (este - self.hoy).days
