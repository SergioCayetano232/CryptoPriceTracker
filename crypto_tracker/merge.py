"""/merge: los años desde que Ethereum dejó la minería y lo que falta para cumplir."""

from dataclasses import dataclass
from datetime import date

# El bloque del cambio salió por la mañana en España, así que no hay lío de fechas.
FECHA = date(2022, 9, 15)


@dataclass(frozen=True)
class Merge:
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
        """Días para el próximo 15 de septiembre. 0 si es hoy."""
        este = FECHA.replace(year=self.hoy.year)
        if este < self.hoy:
            este = este.replace(year=self.hoy.year + 1)
        return (este - self.hoy).days
