"""La comisión de /compra o /venta: 'com 1.5' en dinero o 'com 0.1%' de lo movido."""

from .movimientos import MovimientoError
from .puntuales import numero

PALABRAS = ("com", "comision", "comisión", "fee")


class ComisionError(MovimientoError):
    """Hereda para que /compra y /venta la cojan con sus otros errores."""


def separar(argumento: str) -> tuple[str, str | None]:
    """'btc 0.01 600 com 1.5' -> ('btc 0.01 600', '1.5'). Sin comisión, None."""
    partes = argumento.split()
    for i, parte in enumerate(partes):
        if parte.lower() not in PALABRAS:
            continue
        if i != len(partes) - 2:
            raise ComisionError(
                "La comisión va al final y con su número: com 1.5 o com 0.1%"
            )
        return " ".join(partes[:i]), partes[i + 1]
    return argumento, None


def calcular(texto: str, importe: float) -> float:
    """'1.5' son 1,5 en dinero; '0.1%', esa parte de lo que pagaste o te dieron."""
    en_pct = texto.endswith("%")
    valor = numero(texto.removesuffix("%"))
    if valor is None or valor < 0:
        raise ComisionError(f"'{texto}' no es una comisión. Ej: com 1.5 o com 0.1%")
    if not en_pct:
        return valor
    # Un 100% o más ya no es una comisión, es una errata.
    if valor >= 100:
        raise ComisionError("Una comisión del 100 % o más no puede ser.")
    return importe * valor / 100


def de_venta(cobrado: float, comision: float) -> float:
    """Lo que te queda de verdad después de pagarla."""
    if comision > cobrado:
        raise ComisionError("La comisión es más que lo que te dieron por la venta.")
    return cobrado - comision
