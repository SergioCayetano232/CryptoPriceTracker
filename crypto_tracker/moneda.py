"""La moneda que pides al final de /precio, si no quieres la del .env."""

from .alerts import SIMBOLOS
from .convertir import NOMBRES

# usd, $, dólares... todos a su código.
_MONEDAS = {codigo: codigo for codigo in SIMBOLOS}
_MONEDAS.update({s: codigo for codigo, s in SIMBOLOS.items()})
_MONEDAS.update({n: codigo for codigo, nombres in NOMBRES.items() for n in nombres})


def separar(argumento: str) -> tuple[str, str | None]:
    """'btc eth usd' -> ('btc eth', 'usd'). Sin moneda al final, None."""
    partes = argumento.split()
    if partes and partes[-1].lower() in _MONEDAS:
        return " ".join(partes[:-1]), _MONEDAS[partes.pop().lower()]
    return argumento, None
