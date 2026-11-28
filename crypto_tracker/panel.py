"""El panel web: lo que tienes, lo que vigilas y tus alertas, en una página."""

import hmac
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

from .avisados import Aviso
from .config import Posicion, Watch
from .puntuales import CARTERA, Puntual

# Más puntos que esto no se ven en pantalla y solo engordan la página.
PUNTOS_GRAFICA = 160
PUNTOS_MINI = 40

# Para abrir el panel a la red de casa: más corta se adivina probando.
MIN_CLAVE = 16

# Si en tres consultas seguidas no ha guardado nada, algo le pasa al bot.
CICLOS_PARADO = 3


@dataclass(frozen=True)
class Fila:
    """Una cripto de la cartera."""

    coin_id: str
    cantidad: float
    precio: float
    valor: float
    invertido: float | None
    cambio_24h: float | None
    peso: float
    linea: list[float] = field(default_factory=list)

    @property
    def ganancia(self) -> float | None:
        return None if self.invertido is None else self.valor - self.invertido

    @property
    def porcentaje(self) -> float | None:
        if not self.invertido:
            return None
        return (self.valor / self.invertido - 1) * 100


@dataclass(frozen=True)
class Vigilada:
    coin_id: str
    watch: Watch
    precio: float | None
    cambio_24h: float | None
    linea: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class Alerta:
    id: int
    coin_id: str
    objetivo: float
    sube: bool
    precio: float | None
    nota: str | None = None

    @property
    def falta(self) -> float | None:
        """Lo que tiene que moverse el precio para que salte, en %."""
        if not self.precio:
            return None
        return (self.objetivo / self.precio - 1) * 100

    @property
    def alcanzada(self) -> bool:
        # Pasa entre que llega al precio y el siguiente ciclo del bot la manda.
        if not self.precio:
            return False
        return (
            self.precio >= self.objetivo if self.sube else self.precio <= self.objetivo
        )


@dataclass(frozen=True)
class Dia:
    """Una casilla del calendario."""

    dia: date
    valor: float | None  # lo que valía tu cartera al cerrar el día
    cambio: float | None  # en % sobre el día anterior


@dataclass(frozen=True)
class Panel:
    moneda: str
    filas: list[Fila]
    vigiladas: list[Vigilada]
    alertas: list[Alerta]
    serie: list[tuple[datetime, float]]
    actualizado: datetime | None
    faltan: list[str] = field(default_factory=list)
    total_antes: float | None = None
    # El último aviso mandado de cada cripto, para los avisos del navegador.
    avisos: dict[str, Aviso] = field(default_factory=dict)
    # El precio de bitcoin en esos 7 días, para la línea de "todo en bitcoin".
    serie_btc: list[tuple[datetime, float]] = field(default_factory=list)
    calendario: list[Dia] = field(default_factory=list)

    @property
    def total(self) -> float | None:
        return sum(f.valor for f in self.filas) if self.filas else None

    @property
    def invertido(self) -> float | None:
        if not self.filas or any(f.invertido is None for f in self.filas):
            return None
        return sum(f.invertido for f in self.filas)

    @property
    def ganancia(self) -> float | None:
        if self.total is None or self.invertido is None:
            return None
        return self.total - self.invertido

    @property
    def porcentaje(self) -> float | None:
        if not self.invertido or self.ganancia is None:
            return None
        return self.ganancia / self.invertido * 100

    @property
    def cambio_24h(self) -> float | None:
        return cambio(self.total, self.total_antes)


def cambio(ahora: float | None, antes: float | None) -> float | None:
    if ahora is None or not antes:
        return None
    return (ahora / antes - 1) * 100


def muestrear(valores: list, n: int) -> list:
    """Como mucho n, repartidos, y siempre con el último: es el de ahora."""
    if len(valores) <= n:
        return list(valores)
    paso = (len(valores) - 1) / (n - 1)
    return [valores[round(i * paso)] for i in range(n)]


def filas_cartera(
    posiciones: list[Posicion],
    precios: dict[str, float],
    antes: dict[str, float],
    lineas: dict[str, list[float]],
) -> tuple[list[Fila], list[str]]:
    """Las de la cartera, de la que más vale a la que menos, y las sin precio."""
    con_precio = [p for p in posiciones if precios.get(p.coin_id) is not None]
    faltan = [p.coin_id for p in posiciones if precios.get(p.coin_id) is None]
    total = sum(p.cantidad * precios[p.coin_id] for p in con_precio)

    filas = [
        Fila(
            p.coin_id,
            p.cantidad,
            precios[p.coin_id],
            p.cantidad * precios[p.coin_id],
            p.invertido,
            cambio(precios[p.coin_id], antes.get(p.coin_id)),
            p.cantidad * precios[p.coin_id] / total * 100 if total else 0.0,
            muestrear(lineas.get(p.coin_id, []), PUNTOS_MINI),
        )
        for p in con_precio
    ]
    return sorted(filas, key=lambda f: f.valor, reverse=True), faltan


def total_antes(posiciones: list[Posicion], antes: dict[str, float]) -> float | None:
    """Lo que valía ayer lo que tienes hoy. Sin el de una, no hay con qué comparar."""
    if not posiciones or any(antes.get(p.coin_id) is None for p in posiciones):
        return None
    return sum(p.cantidad * antes[p.coin_id] for p in posiciones)


def alertas(
    puntuales: list[Puntual], precios: dict[str, float], valor_cartera: float | None
) -> list[Alerta]:
    """Las de /alerta, primero las que están más cerca de saltar."""
    lista = [
        Alerta(
            p.id,
            p.coin_id,
            p.objetivo,
            p.sube,
            valor_cartera if p.coin_id == CARTERA else precios.get(p.coin_id),
            p.nota,
        )
        for p in puntuales
    ]
    # Las que no tienen precio, al final: no se sabe lo que les falta.
    return sorted(lista, key=lambda a: (a.falta is None, abs(a.falta or 0)))


def clave_panel() -> str:
    """La de PANEL_CLAVE en el .env. Nunca se enseña ni se loguea."""
    return os.getenv("PANEL_CLAVE", "").strip()


def acceso(ruta: str, clave: str) -> bool:
    """Si la petición trae la clave. Sin clave puesta, el panel es solo local y
    no hace falta."""
    if not clave:
        return True
    dada = parse_qs(urlsplit(ruta).query).get("clave", [""])[0]
    # compare_digest tarda lo mismo acierte o no: no da pistas de por dónde va.
    return hmac.compare_digest(dada.encode(), clave.encode())


def a_json(p: "Panel", parado_: bool) -> dict:
    """Lo justo para un widget: el total, cómo va y cada cripto."""
    return {
        "moneda": p.moneda,
        "total": p.total,
        "cambio_24h": p.cambio_24h,
        "ganancia": p.ganancia,
        "porcentaje": p.porcentaje,
        "actualizado": p.actualizado.isoformat() if p.actualizado else None,
        "parado": parado_,
        "criptos": [
            {
                "id": f.coin_id,
                "valor": f.valor,
                "cambio_24h": f.cambio_24h,
                "peso": f.peso,
            }
            for f in p.filas
        ],
    }


def parado(actualizado: datetime | None, ahora: datetime, intervalo: int) -> bool:
    if actualizado is None:
        return True
    return ahora - actualizado > timedelta(seconds=intervalo * CICLOS_PARADO)


def hace(actualizado: datetime | None, ahora: datetime) -> str:
    if actualizado is None:
        return "todavía sin precios"
    segundos = max(0, int((ahora - actualizado).total_seconds()))
    if segundos < 60:
        return "hace un momento"
    minutos = segundos // 60
    if minutos < 60:
        return f"hace {minutos} min"
    horas = minutos // 60
    if horas < 48:
        return f"hace {horas} h"
    return f"hace {horas // 24} días"


def en_bitcoin(
    serie: list[tuple[datetime, float]], btc: list[tuple[datetime, float]]
) -> list[float]:
    """Lo que valdría la cartera si al principio de la serie lo hubieras pasado
    todo a bitcoin. Vacío si no hay precio de bitcoin para ese principio."""
    btc = sorted(btc)
    valores, i, ultimo = [], 0, None
    for cuando, _ in serie:
        # El último precio guardado hasta ese momento: no van a la misma hora.
        while i < len(btc) and btc[i][0] <= cuando:
            ultimo = btc[i][1]
            i += 1
        if ultimo is None:
            return []
        valores.append(ultimo)
    return [serie[0][1] * v / valores[0] for v in valores]


def dias_cartera(
    posiciones: list[Posicion],
    cierres: list[tuple[date, str, float]],
    hoy: date,
    semanas: int = 53,
) -> list[Dia]:
    """Semanas enteras, de lunes a domingo, desde el primer día con precio (y
    como mucho un año) hasta la de hoy. Con lo que tienes ahora, no con lo que
    tenías entonces: es cómo le ha ido a tu reparto de hoy."""
    cantidades = {p.coin_id: p.cantidad for p in posiciones}
    precios: dict[date, dict[str, float]] = {}
    for dia, coin_id, precio in cierres:
        if coin_id in cantidades:
            precios.setdefault(dia, {})[coin_id] = precio

    valores = {
        dia: sum(cantidades[c] * p[c] for c in cantidades)
        for dia, p in precios.items()
        # Sin el de una, el total saldría hundido ese día.
        if all(c in p for c in cantidades)
    }
    if not valores:
        return []

    lunes_hoy = hoy - timedelta(days=hoy.weekday())
    primero = min(valores)
    inicio = max(
        primero - timedelta(days=primero.weekday()),
        lunes_hoy - timedelta(weeks=semanas - 1),
    )
    dias = []
    dia = inicio
    while dia <= lunes_hoy + timedelta(days=6):
        valor = valores.get(dia)
        ayer = valores.get(dia - timedelta(days=1))
        dias.append(Dia(dia, valor, cambio(valor, ayer)))
        dia += timedelta(days=1)
    return dias


def trazo(
    valores: list[float],
    ancho: float,
    alto: float,
    escala: tuple[float, float] | None = None,
) -> str:
    """La línea en un path de SVG. Vacío si no hay al menos dos puntos.

    escala es (suelo, techo), para que dos líneas compartan alturas."""
    if len(valores) < 2:
        return ""
    suelo, techo = escala or (min(valores), max(valores))
    # Plano: a media altura, que dividir por cero no dibuja nada.
    rango = techo - suelo or 1
    medio = 0.5 if techo == suelo else None
    paso = ancho / (len(valores) - 1)

    puntos = []
    for i, v in enumerate(valores):
        y = alto * (1 - (medio if medio is not None else (v - suelo) / rango))
        puntos.append(f"{i * paso:.1f},{y:.1f}")
    return "M" + " L".join(puntos)
