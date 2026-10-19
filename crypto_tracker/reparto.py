"""/reparto: qué parte de la cartera es cada cripto."""

from dataclasses import dataclass

from .cartera import Valor

# Con más trozos los colores ya se confunden; el resto va junto en "Otras".
MAXIMO = 6

OTRAS = "otras"

# Por encima de esto, si esa cae se lleva media cartera con ella.
MUCHO = 50


@dataclass(frozen=True)
class Trozo:
    coin_id: str  # OTRAS si junta varias
    valor: float
    peso: float  # en %
    color: int | None  # posición en la paleta; None para "Otras", que va en gris


def trozos(valores: list[Valor]) -> list[Trozo]:
    """De más a menos. valores va en el orden de la cartera, que fija los colores."""
    con_valor = [v for v in valores if v.valor > 0]
    total = sum(v.valor for v in con_valor)
    if not total:
        return []

    grandes = sorted(con_valor, key=lambda v: v.valor, reverse=True)
    resto = []
    if len(grandes) > MAXIMO:
        grandes, resto = grandes[: MAXIMO - 1], grandes[MAXIMO - 1 :]

    # El color va por su sitio en la cartera, no por tamaño: así bitcoin es
    # siempre azul aunque un día ethereum valga más.
    orden = [v.coin_id for v in con_valor if v in grandes]
    lista = [
        Trozo(v.coin_id, v.valor, v.valor / total * 100, orden.index(v.coin_id))
        for v in grandes
    ]
    if resto:
        junto = sum(v.valor for v in resto)
        lista.append(Trozo(OTRAS, junto, junto / total * 100, None))
    return lista


def demasiado(lista: list[Trozo]) -> Trozo | None:
    """La que se come más de la mitad de la cartera, si hay alguna."""
    # Con una sola, que sea el 100% ya lo sabes.
    if len(lista) < 2 or lista[0].coin_id == OTRAS:
        return None
    return lista[0] if lista[0].peso > MUCHO else None
