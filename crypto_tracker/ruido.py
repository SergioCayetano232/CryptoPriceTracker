"""/ruido: cuántos avisos de /vigilar se dieron la vuelta enseguida, y un % mejor."""

from bisect import bisect_right
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from .alerts import ALTO, revisar
from .nucleo.config import Watch
from .nucleo.periodo import PeriodoError, es_tramo, leer
from .nucleo.simbolos import a_id
from .voto import SIN_VOTOS, Votos

POR_DEFECTO = 30 * 24
VENTANA = timedelta(hours=24)

# Con menos avisos ya cerrados, el porcentaje es pura casualidad.
MINIMO = 3
# Más de un tercio en falso ya es para cambiar la regla.
MUCHO = 1 / 3

PORCENTAJES = (1, 2, 3, 4, 5, 7, 10, 15, 20, 25, 30)
VECES_PASO = (2, 3, 4, 5, 10)


@dataclass(frozen=True)
class Simulado:
    cuando: datetime
    precio: float
    vuelta: float  # si lo vuelve a cruzar en menos de VENTANA, fue en falso
    sube: bool


@dataclass(frozen=True)
class Cuenta:
    avisos: int
    falsos: int
    pendientes: int  # los de las últimas 24 h: aún no se sabe

    @property
    def cerrados(self) -> int:
        return self.avisos - self.pendientes

    @property
    def proporcion(self) -> float | None:
        return self.falsos / self.cerrados if self.cerrados else None

    @property
    def mucho(self) -> bool:
        return self.cerrados >= MINIMO and self.proporcion > MUCHO


@dataclass(frozen=True)
class Ruido:
    watch: Watch
    cuenta: Cuenta
    propuesta: tuple[Watch, Cuenta] | None = None
    votos: Votos = SIN_VOTOS  # tus 👍 y 👎 del tramo


def interpretar(argumento: str) -> tuple[str, float]:
    """'bitcoin 7d' -> ('bitcoin', 168). Sin tramo, 30 días; sin cripto, ''."""
    partes = argumento.split()
    horas = POR_DEFECTO
    if partes and es_tramo(partes[-1]):
        horas = leer(partes.pop())
    if len(partes) > 1:
        raise PeriodoError("Escríbelo así: /ruido bitcoin 30d")
    # Hacen falta 24 h detrás de cada aviso para saber si fue en falso.
    if horas < 48:
        raise PeriodoError("Necesito al menos 2 días, por ejemplo 7d")
    return (a_id(partes[0]) if partes else ""), horas


def simular(serie: list[tuple[datetime, float]], watch: Watch) -> list[Simulado]:
    """Los avisos que habría mandado la regla, con la misma cuenta que el bot."""
    estado: dict[str, str] = {}
    lista = []
    for i, (cuando, precio) in enumerate(serie):
        alertas, estado = revisar({watch.coin_id: precio}, [watch], estado)
        # El primer precio solo coloca el estado. Si no, un precio fijo ya
        # cruzado antes del tramo contaría como aviso.
        if i == 0:
            continue
        for a in alertas:
            # Las de % avisan tras moverse un tramo entero: con que deshaga
            # la mitad ya me parece aviso en falso.
            if a.percent is not None:
                vuelta = (a.threshold + a.price) / 2
            else:
                vuelta = a.threshold
            lista.append(Simulado(cuando, precio, vuelta, a.estado == ALTO))
    return lista


def contar(serie: list[tuple[datetime, float]], avisos: list[Simulado]) -> Cuenta:
    if not serie:
        return Cuenta(0, 0, 0)
    fechas = [c for c, _ in serie]
    ultimo = fechas[-1]

    falsos = pendientes = 0
    for s in avisos:
        hasta = s.cuando + VENTANA
        if ultimo < hasta:
            pendientes += 1
            continue
        despues = serie[bisect_right(fechas, s.cuando) : bisect_right(fechas, hasta)]
        if s.sube:
            falsos += any(p <= s.vuelta for _, p in despues)
        else:
            falsos += any(p >= s.vuelta for _, p in despues)
    return Cuenta(len(avisos), falsos, pendientes)


def candidatas(watch: Watch) -> list[Watch]:
    """Reglas más anchas que la tuya, de la que menos cambia a la que más."""
    if watch.percent is not None:
        return [replace(watch, percent=p) for p in PORCENTAJES if p > watch.percent]
    if watch.step is not None:
        # Si ningún paso más ancho vale, pruebo con %: el paso fijo rebota
        # mucho cuando el precio se queda dando vueltas a un nivel.
        pasos = [replace(watch, step=watch.step * k) for k in VECES_PASO]
        return pasos + [Watch(watch.coin_id, percent=p) for p in PORCENTAJES]
    # Un precio fijo lo eliges tú por algo; no me invento otro.
    return []


def analizar(
    serie: list[tuple[datetime, float]], watch: Watch, votos: Votos = SIN_VOTOS
) -> Ruido:
    """votos son tus 👍 y 👎 a los avisos de esa cripto en el tramo."""
    cuenta = contar(serie, simular(serie, watch))
    if cuenta.mucho:
        for otra in candidatas(watch):
            suya = contar(serie, simular(serie, otra))
            # Una que no avise nunca no tiene falsos, pero tampoco sirve.
            if suya.cerrados and suya.proporcion <= MUCHO:
                return Ruido(watch, cuenta, (otra, suya), votos)
        return Ruido(watch, cuenta, votos=votos)

    # El precio no dice que haya ruido, pero tú sí: la primera que avise menos
    # sin quedarse muda.
    if votos.muchos_sobran:
        for otra in candidatas(watch):
            suya = contar(serie, simular(serie, otra))
            if 0 < suya.avisos < cuenta.avisos:
                return Ruido(watch, cuenta, (otra, suya), votos)
    return Ruido(watch, cuenta, votos=votos)
