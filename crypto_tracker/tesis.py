"""/tesis: apuntar por qué compras y, pasado un tiempo, ver si acertaste."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from .simbolos import a_id

EJEMPLO = "/tesis sol el ETF lo va a subir"
DIAS = 30
MIN_DIAS, MAX_DIAS = 7, 365
MAX_TEXTO = 300
# Con más pendientes ya no es pensar cada compra, es un diario.
MAXIMO = 20

SI = {"si", "sí", "acerte", "acerté"}
NO = {"no", "falle", "fallé"}
QUITAR = {"quitar", "borrar"}

_PLAZO = re.compile(r"(\d+)d", re.IGNORECASE)


class TesisError(Exception):
    """Lo que escribiste en /tesis no se entiende."""


@dataclass(frozen=True)
class Tesis:
    numero: int
    coin_id: str
    texto: str
    precio: float
    cuando: datetime
    dias: int = DIAS
    # El precio el día que te pregunté. None mientras no ha llegado.
    final: float | None = None
    acerto: bool | None = None

    @property
    def vence(self) -> datetime:
        return self.cuando + timedelta(days=self.dias)

    @property
    def preguntada(self) -> bool:
        return self.final is not None

    def cambio(self, precio: float) -> float:
        return (precio / self.precio - 1) * 100


@dataclass(frozen=True)
class Nueva:
    coin_id: str
    dias: int
    texto: str


@dataclass(frozen=True)
class Veredicto:
    numero: int
    acerto: bool


@dataclass(frozen=True)
class Quitar:
    numero: int


def interpretar(argumento: str) -> Nueva | Veredicto | Quitar:
    """'sol 90d sube con el ETF', 'si 3', 'no 3' o 'quitar 3'."""
    partes = argumento.split(maxsplit=1)
    if not partes:
        raise TesisError(f"Escribe la cripto y por qué la compras: {EJEMPLO}")
    primera = partes[0].lower()
    if primera in SI | NO | QUITAR:
        numero = _numero(partes[1] if len(partes) > 1 else "")
        if primera in QUITAR:
            return Quitar(numero)
        return Veredicto(numero, primera in SI)

    resto = partes[1].split(maxsplit=1) if len(partes) > 1 else []
    dias = DIAS
    if resto and _PLAZO.fullmatch(resto[0]):
        dias = int(resto[0][:-1])
        if not MIN_DIAS <= dias <= MAX_DIAS:
            raise TesisError(
                f"El plazo, entre {MIN_DIAS} y {MAX_DIAS} días. "
                "Menos de una semana es ruido."
            )
        resto = resto[1:]
    texto = " ".join(resto).strip()
    if not texto:
        raise TesisError(f"¿Y por qué? Escríbelo detrás: {EJEMPLO}")
    if len(texto) > MAX_TEXTO:
        raise TesisError(
            f"Muy largo: como mucho {MAX_TEXTO} letras. Si no cabe en un par de "
            "frases, igual no lo tienes tan claro."
        )
    return Nueva(a_id(partes[0]), dias, texto)


def _numero(texto: str) -> int:
    try:
        return int(texto.strip().lstrip("#"))
    except ValueError:
        raise TesisError("Falta el número de la tesis. Las tienes en /tesis") from None


def siguiente(lista: list[Tesis]) -> int:
    return max((t.numero for t in lista), default=0) + 1


def pendientes(lista: list[Tesis]) -> list[Tesis]:
    return [t for t in lista if not t.preguntada]


def tocan(lista: list[Tesis], ahora: datetime) -> list[Tesis]:
    return [t for t in pendientes(lista) if ahora >= t.vence]


def marcador(lista: list[Tesis]) -> tuple[int, int]:
    """(aciertos, juzgadas). Las que no has contestado no cuentan."""
    juzgadas = [t for t in lista if t.acerto is not None]
    return sum(t.acerto for t in juzgadas), len(juzgadas)


def a_texto(t: Tesis) -> str:
    """Como va en ajustes. El texto, al final: puede llevar '|' y todo."""
    final = "" if t.final is None else repr(t.final)
    acerto = "" if t.acerto is None else ("si" if t.acerto else "no")
    return (
        f"{t.cuando.isoformat(timespec='seconds')}|{t.precio!r}|{t.dias}|"
        f"{final}|{acerto}|{t.coin_id}|{t.texto}"
    )


def de_texto(numero: int, valor: str) -> Tesis | None:
    try:
        cuando, precio, dias, final, acerto, coin_id, texto = valor.split("|", 6)
        return Tesis(
            numero,
            coin_id,
            texto,
            float(precio),
            datetime.fromisoformat(cuando),
            int(dias),
            float(final) if final else None,
            {"si": True, "no": False}.get(acerto),
        )
    except ValueError:
        return None
