"""/whitepaper: los años del documento de Satoshi y lo que falta para cumplir."""

from dataclasses import dataclass
from datetime import date

# El día que lo mandó a la lista de correo de criptografía.
PUBLICADO = date(2008, 10, 31)


@dataclass(frozen=True)
class Whitepaper:
    hoy: date

    @property
    def dias(self) -> int:
        return (self.hoy - PUBLICADO).days

    @property
    def años(self) -> int:
        este = PUBLICADO.replace(year=self.hoy.year)
        return self.hoy.year - PUBLICADO.year - (self.hoy < este)

    @property
    def faltan(self) -> int:
        """Días para el próximo 31 de octubre. 0 si es hoy."""
        este = PUBLICADO.replace(year=self.hoy.year)
        if este < self.hoy:
            este = este.replace(year=self.hoy.year + 1)
        return (este - self.hoy).days
