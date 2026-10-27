"""/sueldo: tu cartera en meses de salario mínimo."""

from dataclasses import dataclass

# El SMI de 2026, 1.221 € en 14 pagas. Lo reparto en 12 para que un mes sea un mes.
PAGA = 1221
ANUAL = PAGA * 14
MENSUAL = ANUAL / 12


@dataclass(frozen=True)
class Sueldo:
    valor: float  # lo que vale tu cartera

    @property
    def meses(self) -> float:
        return self.valor / MENSUAL
