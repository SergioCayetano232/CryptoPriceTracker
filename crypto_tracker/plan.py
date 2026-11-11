"""/plan: cuánto tardas en llegar a una cifra metiendo lo mismo cada semana."""

from dataclasses import dataclass
from datetime import date, timedelta

from .puntuales import numero

EJEMPLO = "/plan 10000 50 semanal"

# Como en /dca, un mes son 30 días.
DIAS = {"diario": 1, "semanal": 7, "mensual": 30}
POR_AÑO = {"diario": 365, "semanal": 52, "mensual": 12}
TEXTO = {"diario": "cada día", "semanal": "cada semana", "mensual": "cada mes"}

# Más allá de esto no es un plan, es una herencia.
MAX_AÑOS = 100


class PlanError(Exception):
    """Lo que escribiste en /plan no se entiende."""


@dataclass(frozen=True)
class Peticion:
    meta: float
    aporte: float
    frecuencia: str = "semanal"
    anual: float = 0.0  # lo que crees que sacará al año, en %


@dataclass(frozen=True)
class Camino:
    peticion: Peticion
    inicio: float  # lo que ya tienes
    veces: int | None  # aportes hasta llegar; None si no llega en MAX_AÑOS
    final: float = 0.0

    @property
    def dias(self) -> int | None:
        if self.veces is None:
            return None
        return self.veces * DIAS[self.peticion.frecuencia]

    @property
    def metido(self) -> float:
        return (self.veces or 0) * self.peticion.aporte

    @property
    def intereses(self) -> float:
        return self.final - self.inicio - self.metido

    def fecha(self, hoy: date) -> date | None:
        return None if self.dias is None else hoy + timedelta(days=self.dias)


def interpretar(argumento: str) -> Peticion:
    """'10000 50 semanal al 8%' -> Peticion(10000, 50, 'semanal', 8)."""
    partes = [
        p for p in argumento.lower().split() if p not in {"al", "a", "€", "$", "£"}
    ]
    if not 2 <= len(partes) <= 4:
        raise PlanError(
            f"Escríbelo así: {EJEMPLO} (a cuánto quieres llegar y lo que metes). "
            "Si crees que va a dar algo al año, añádelo: /plan 10000 50 semanal 8%"
        )

    meta = numero(partes[0])
    if meta is None or meta <= 0:
        raise PlanError(f"'{partes[0]}' no es una cifra. Ej: {EJEMPLO}")
    aporte = numero(partes[1])
    if aporte is None or aporte <= 0:
        raise PlanError(f"'{partes[1]}' no es lo que metes. Ej: {EJEMPLO}")

    frecuencia, anual = "semanal", 0.0
    for parte in partes[2:]:
        if parte in DIAS:
            frecuencia = parte
        elif parte.endswith("%") and numero(parte[:-1]) is not None:
            anual = numero(parte[:-1])
            if not -100 < anual <= 1000:
                raise PlanError(f"'{parte}' al año no tiene sentido. Ej: 8%")
        else:
            raise PlanError(
                f"No entiendo '{parte}': va diario, semanal o mensual, y lo que "
                "crees que dará al año, en %. Ej: /plan 10000 50 semanal 8%"
            )
    return Peticion(meta, aporte, frecuencia, anual)


def calcular(p: Peticion, inicio: float = 0.0) -> Camino:
    if inicio >= p.meta:
        return Camino(p, inicio, 0, inicio)

    # El interés de cada tramo, sacado del anual para que al año dé lo que dices.
    tramo = (1 + p.anual / 100) ** (1 / POR_AÑO[p.frecuencia]) - 1
    valor, veces = inicio, 0
    while valor < p.meta:
        if veces >= MAX_AÑOS * POR_AÑO[p.frecuencia]:
            return Camino(p, inicio, None)
        # Primero crece lo que hay y luego entra el aporte, que aún no ha rendido.
        valor = valor * (1 + tramo) + p.aporte
        veces += 1
    return Camino(p, inicio, veces, valor)


def cuanto(dias: int) -> str:
    """'3 semanas', '5 meses' o '2 años y 3 meses'."""
    if dias < 60:
        semanas = round(dias / 7)
        if semanas < 2:
            return "1 día" if dias == 1 else f"{dias} días"
        return f"{semanas} semanas"
    años, meses = divmod(round(dias / 30.4), 12)
    trozos = []
    if años:
        trozos.append("1 año" if años == 1 else f"{años} años")
    if meses:
        trozos.append("1 mes" if meses == 1 else f"{meses} meses")
    return " y ".join(trozos)
