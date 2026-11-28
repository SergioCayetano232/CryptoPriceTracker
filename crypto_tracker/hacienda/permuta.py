"""/permuta: lo que pagas a Hacienda al cambiar una cripto por otra, sin tocar euros."""

from dataclasses import dataclass

from .. import comision
from ..config import Posicion
from ..movimientos import Movimiento, MovimientoError, interpretar_venta
from ..simbolos import a_id
from . import sivendo
from .impuestos import Impuestos
from .sivendo import Simulacion

EJEMPLO = (
    "/permuta btc eth 0.01, /permuta btc eth todo o /permuta btc eth 0.01 com 0.1%"
)


@dataclass(frozen=True)
class Permuta:
    venta: Simulacion  # lo que Hacienda ve: una venta al valor de mercado
    destino: str
    recibes: float
    precio_destino: float
    comision: float

    @property
    def valor(self) -> float:
        """Lo que vale lo que te llevas. Es lo que contará como coste al venderla."""
        return self.recibes * self.precio_destino


def interpretar(argumento: str) -> tuple[str, str, float | None, str | None]:
    """'btc eth 0.01 com 0.1%' -> ('bitcoin', 'ethereum', 0.01, '0.1%')."""
    try:
        argumento, texto_comision = comision.separar(argumento)
        partes = argumento.split()
        if len(partes) != 3:
            raise MovimientoError
        origen, cantidad, _ = interpretar_venta(f"{partes[0]} {partes[2]}")
    except MovimientoError:
        raise MovimientoError(f"Escríbelo así: {EJEMPLO}") from None
    destino = a_id(partes[1])
    if destino == origen:
        raise MovimientoError("Eso es cambiarla por ella misma: pon otra cripto.")
    return origen, destino, cantidad, texto_comision


def calcular(
    antes: Posicion,
    vendido: float,
    precio_origen: float,
    destino: str,
    precio_destino: float,
    queda: Posicion | None,
    este_año: Impuestos,
    historia: list[Movimiento] | tuple = (),
    texto_comision: str | None = None,
) -> Permuta:
    bruto = vendido * precio_origen
    pagada = comision.calcular(texto_comision, bruto) if texto_comision else 0.0
    # La comisión se queda en el exchange: ni te llega en la otra ni cuenta como
    # lo que te dieron, igual que en /venta.
    neto = comision.de_venta(bruto, pagada)
    venta = sivendo.calcular(antes, vendido, neto, queda, este_año, historia)
    return Permuta(venta, destino, neto / precio_destino, precio_destino, pagada)
