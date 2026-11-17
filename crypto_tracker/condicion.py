"""La segunda condición de una /alerta: 'btc 60000 si miedo<20'."""

import re
from dataclasses import dataclass

INDICADORES = ("miedo", "rsi")
EJEMPLO = "/alerta btc 60000 si miedo<20"

_DEBAJO = r"<|menos de|por debajo de|baja de|baje de|bajo"
_ENCIMA = r">|mas de|más de|por encima de|sube de|suba de|sobre"
_COLA = re.compile(
    rf"\s+(?:si|y|con)\s+(?:el\s+)?(?P<indicador>[a-zá-ú]+)\s*"
    rf"(?:(?:esta|está|este|esté)\s+)?(?P<lado>{_DEBAJO}|{_ENCIMA})\s*(?P<valor>\S+)$",
    re.IGNORECASE,
)


class CondicionError(Exception):
    """La condición de la /alerta no se entiende."""


@dataclass(frozen=True)
class Condicion:
    indicador: str  # "miedo" o "rsi"
    menor: bool  # True si tiene que estar por debajo
    valor: float

    def guardar(self) -> str:
        return f"{self.indicador}{'<' if self.menor else '>'}{self.valor:g}"

    def cumple(self, actual: float) -> bool:
        return actual < self.valor if self.menor else actual > self.valor


def separar(argumento: str) -> tuple[str, Condicion | None]:
    """'btc 60000 si miedo<20' -> ('btc 60000', miedo < 20)."""
    m = _COLA.search(argumento)
    if not m:
        # Habla del miedo o del RSI pero no lo entiendo: mejor decirlo que
        # tomarlo por una nota y poner una alerta que no es la que pediste.
        # "vender si sigue subiendo" sí es una nota.
        if re.search(r"\s(?:si|y|con)\s+(?:el\s+)?(?:miedo|rsi)\b", argumento, re.I):
            raise CondicionError(f"No entiendo la condición. Escríbela así: {EJEMPLO}")
        return argumento, None

    indicador = m["indicador"].lower()
    if indicador not in INDICADORES:
        # "y algo menos de 5" puede ser una nota; con < o > ya no.
        if m["lado"] not in "<>":
            return argumento, None
        raise CondicionError(
            f"Solo sé mirar el miedo y el RSI. Por ejemplo: {EJEMPLO} o "
            "/alerta eth 2000 si rsi<30"
        )
    try:
        valor = float(m["valor"].replace(",", "."))
    except ValueError:
        raise CondicionError(f"'{m['valor']}' no es un número. Ej: {EJEMPLO}") from None
    # Los dos van de 0 a 100: con 120 no saltaría nunca.
    if not 0 < valor < 100:
        raise CondicionError("El miedo y el RSI van de 0 a 100: pon algo entre medias")

    menor = re.fullmatch(_DEBAJO, m["lado"].lower()) is not None
    return argumento[: m.start()], Condicion(indicador, menor, valor)


def leer(texto: str | None) -> Condicion | None:
    """La de la base de datos. Si no se entiende, como si no tuviera."""
    if not texto:
        return None
    m = re.fullmatch(r"(miedo|rsi)([<>])(\d+(?:\.\d+)?)", texto)
    if not m:
        return None
    return Condicion(m[1], m[2] == "<", float(m[3]))
