"""/ciclo: lo que dicen a la vez los indicadores de largo plazo de bitcoin.

Como /semaforo, cada uno vota: 1 si dice que está barato (cerca de un fondo),
-1 si caro (cerca de un techo) y 0 si en medio.
"""

from .ahr999 import COMPRAR, ESPERAR, Ahr999
from .arcoiris import FRANJAS, Arcoiris
from .hashribbons import Ribbons
from .mayer import BURBUJA, Mayer
from .mvrv import Mvrv
from .picycle import PiCycle
from .semaforo import Voto
from .suelo import Suelo

FONDO, MEDIO, TECHO = "fondo", "medio", "techo"
# Igual que en /semaforo: con uno de diferencia sigue siendo un empate.
MARGEN = 2
MIN_VOTOS = 3


def _num(valor: float, decimales: int = 2) -> str:
    return f"{valor:.{decimales}f}".replace(".", ",")


def de_mayer(m: Mayer) -> Voto:
    nombre = f"Mayer {_num(m.hoy.multiple)}"
    if m.hoy.multiple < 1:
        return Voto(nombre, 1, "por debajo de su media de 200 días")
    if m.hoy.multiple >= BURBUJA:
        return Voto(nombre, -1, "en zona de burbuja")
    return Voto(nombre, 0, "por encima de su media, sin pasarse")


def de_arcoiris(a: Arcoiris) -> Voto:
    franja = a.franja
    nombre = "Arcoíris"
    motivo = f"«{FRANJAS[franja]}»"
    if franja <= 3:
        return Voto(nombre, 1, motivo)
    if franja >= 6:
        return Voto(nombre, -1, motivo)
    return Voto(nombre, 0, motivo)


def de_suelo(s: Suelo) -> Voto:
    distancia = s.hoy.distancia
    nombre = "200 semanas"
    if distancia < 0:
        return Voto(nombre, 1, f"un {-distancia:.0f}% por debajo de la media")
    donde = f"un {distancia:.0f}% por encima de la media"
    if distancia < 50:
        return Voto(nombre, 1, f"{donde}, cerca del suelo")
    if distancia >= 150:
        return Voto(nombre, -1, f"{donde}, lejos del suelo")
    return Voto(nombre, 0, donde)


def de_picycle(p: PiCycle) -> Voto:
    ratio = p.hoy.ratio
    nombre = "Pi Cycle"
    if ratio >= 0.9:
        return Voto(nombre, -1, "las medias a punto de cruzarse o cruzadas")
    # Solo avisa de techos: lejos de cruzarse no dice que esté barato.
    return Voto(nombre, 0, f"la rápida al {ratio * 100:.0f}% de la otra, lejos")


def de_ahr999(a: Ahr999) -> Voto:
    indice = a.hoy.indice
    nombre = f"ahr999 {_num(indice)}"
    if indice < COMPRAR:
        return Voto(nombre, 1, "zona de comprar fuerte")
    if indice >= ESPERAR:
        return Voto(nombre, -1, "zona de esperar")
    return Voto(nombre, 0, "zona de DCA")


def de_mvrv(m: Mvrv) -> Voto:
    z = m.hoy.z
    nombre = f"MVRV Z {_num(z)}"
    if z < 2:
        return Voto(nombre, 1, "cerca de lo que pagaron de media")
    if z >= 5:
        return Voto(nombre, -1, "muy por encima de lo que pagaron")
    return Voto(nombre, 0, "en lo normal")


def de_hashribbons(r: Ribbons) -> Voto:
    nombre = "Hash ribbons"
    estado = r.estado
    if estado == "señal":
        return Voto(nombre, 1, "acaba de terminar una capitulación")
    if estado == "capitula":
        # Es de fondo, pero la señal es cuando acaba, no mientras dura.
        return Voto(nombre, 0, "los mineros capitulando; la señal es al acabar")
    if estado == "cruzando":
        return Voto(nombre, 0, "las medias se acaban de cruzar a la baja")
    return Voto(nombre, 0, "minado sano")


def veredicto(votos: list[Voto]) -> str:
    """FONDO, TECHO o MEDIO. Con pocos votos, MEDIO."""
    if len(votos) < MIN_VOTOS:
        return MEDIO
    fondo = sum(v.valor > 0 for v in votos)
    techo = sum(v.valor < 0 for v in votos)
    if fondo - techo >= MARGEN:
        return FONDO
    if techo - fondo >= MARGEN:
        return TECHO
    return MEDIO
