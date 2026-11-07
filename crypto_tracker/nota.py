"""El porqué de una /compra o /venta: lo que va detrás de los números."""

from .comision import PALABRAS
from .movimientos import MovimientoError
from .puntuales import MAX_NOTA, numero


def separar(argumento: str) -> tuple[str, str | None]:
    """'btc 0.01 600 com 1 por el halving' -> ('btc 0.01 600 com 1', 'por el halving').

    Va por posiciones: cripto, cantidad, el precio si lo hay y la comisión si la hay.
    Lo que sobra es la nota.
    """
    partes = argumento.split()
    i = 2
    if len(partes) > i and numero(partes[i].removeprefix("@")) is not None:
        i += 1
    if len(partes) > i and partes[i].lower() in PALABRAS:
        # "com" sin nada detrás no es una nota: que avise comision.separar.
        if len(partes) == i + 1:
            return argumento, None
        i += 2
    nota = " ".join(partes[i:])
    if not nota:
        return argumento, None
    if len(nota) > MAX_NOTA:
        raise MovimientoError(f"La nota es muy larga, como mucho {MAX_NOTA} letras.")
    return " ".join(partes[:i]), nota
