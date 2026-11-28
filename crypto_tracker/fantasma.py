"""/fantasma: una cartera de mentira para probar sin arriesgar nada."""

import json
from dataclasses import dataclass, field, replace
from datetime import datetime

from .nucleo.simbolos import a_id
from .puntuales import numero

INICIAL = 1000.0
BITCOIN = "bitcoin"
EJEMPLOS = "/fantasma compra btc 200, /fantasma vende btc todo o /fantasma reinicia"
TODO = {"todo", "todas", "all"}
# Por debajo de un céntimo es lo que sobra de los decimales al venderlo todo.
RESTO = 0.01
# Contra bitcoin, irse menos de esto es ir igual.
EMPATE = 0.5


class FantasmaError(Exception):
    """Lo que escribiste en /fantasma no se entiende o no se puede hacer."""


@dataclass(frozen=True)
class Hueco:
    cantidad: float
    invertido: float  # lo que te costó, para decirte cómo va


@dataclass(frozen=True)
class Fantasma:
    inicio: datetime
    importe: float  # con lo que empezaste
    caja: float  # lo que queda sin invertir
    btc_inicio: float | None  # para compararte con dejarlo todo en bitcoin
    posiciones: dict[str, Hueco] = field(default_factory=dict)
    operaciones: int = 0

    def valor(self, precios: dict[str, float]) -> float | None:
        """None si falta el precio de alguna: mejor no dar un total que mienta."""
        total = self.caja
        for coin_id, h in self.posiciones.items():
            if coin_id not in precios:
                return None
            total += h.cantidad * precios[coin_id]
        return total

    def en_bitcoin(self, precio_btc: float) -> float | None:
        if not self.btc_inicio:
            return None
        return self.importe / self.btc_inicio * precio_btc


def nueva(importe: float, ahora: datetime, precio_btc: float | None) -> Fantasma:
    return Fantasma(ahora, importe, importe, precio_btc)


def interpretar(argumento: str) -> tuple:
    """('ver',), ('compra', id, euros), ('vende', id, cuanto) o ('reinicia', x)."""
    partes = argumento.split()
    if not partes:
        return ("ver",)
    orden = partes[0].lower()

    if orden in ("reinicia", "reiniciar", "empieza", "nueva"):
        if len(partes) == 1:
            return ("reinicia", INICIAL)
        return ("reinicia", _importe(partes[1]))

    if orden in ("compra", "comprar") and len(partes) == 3:
        return ("compra", a_id(partes[1]), _importe(partes[2]))

    if orden in ("vende", "vender", "venta") and len(partes) == 3:
        cuanto = partes[2].lower()
        if cuanto in TODO:
            return ("vende", a_id(partes[1]), ("parte", 1.0))
        if cuanto.endswith("%"):
            pct = numero(cuanto[:-1])
            if pct is None or not 0 < pct <= 100:
                raise FantasmaError("El % tiene que ir de 1 a 100, por ejemplo 50%")
            return ("vende", a_id(partes[1]), ("parte", pct / 100))
        return ("vende", a_id(partes[1]), ("importe", _importe(cuanto)))

    raise FantasmaError(f"Escríbelo así: {EJEMPLOS}")


def _importe(texto: str) -> float:
    valor = numero(texto)
    if valor is None or valor <= 0:
        raise FantasmaError(f"'{texto}' no es un importe. Ejemplos: {EJEMPLOS}")
    return valor


def comprar(f: Fantasma, coin_id: str, euros: float, precio: float) -> Fantasma:
    if euros > f.caja + RESTO:
        raise FantasmaError(
            f"Solo te quedan {_dinero(f.caja)} sin invertir. Vende algo o empieza de "
            "nuevo con /fantasma reinicia"
        )
    euros = min(euros, f.caja)
    antes = f.posiciones.get(coin_id, Hueco(0.0, 0.0))
    hueco = Hueco(antes.cantidad + euros / precio, antes.invertido + euros)
    return replace(
        f,
        caja=f.caja - euros,
        posiciones={**f.posiciones, coin_id: hueco},
        operaciones=f.operaciones + 1,
    )


def vender(
    f: Fantasma, coin_id: str, cuanto: tuple[str, float], precio: float
) -> tuple[Fantasma, float]:
    """cuanto: ('parte', 0.5) o ('importe', 100). Devuelve lo cobrado."""
    h = f.posiciones.get(coin_id)
    if h is None:
        raise FantasmaError("No tienes de esa en la cartera fantasma. Mira /fantasma")

    tipo, valor = cuanto
    vale = h.cantidad * precio
    if tipo == "importe" and valor > vale + RESTO:
        raise FantasmaError(
            f"Solo tienes {_dinero(vale)} de esa. Con 'todo' la vendes entera"
        )
    parte = min(1.0, valor if tipo == "parte" else valor / vale)

    cobrado = h.cantidad * parte * precio
    posiciones = dict(f.posiciones)
    if parte >= 1.0 or h.cantidad * (1 - parte) * precio < RESTO:
        del posiciones[coin_id]
    else:
        posiciones[coin_id] = Hueco(h.cantidad * (1 - parte), h.invertido * (1 - parte))
    nueva_f = replace(
        f, caja=f.caja + cobrado, posiciones=posiciones, operaciones=f.operaciones + 1
    )
    return nueva_f, cobrado


def _dinero(valor: float) -> str:
    """1.000,00, como se escribe aquí."""
    return f"{valor:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def a_texto(f: Fantasma) -> str:
    return json.dumps(
        {
            "inicio": f.inicio.isoformat(timespec="seconds"),
            "importe": f.importe,
            "caja": f.caja,
            "btc_inicio": f.btc_inicio,
            "operaciones": f.operaciones,
            "posiciones": {
                c: [h.cantidad, h.invertido] for c, h in f.posiciones.items()
            },
        }
    )


def de_texto(texto: str) -> Fantasma | None:
    try:
        d = json.loads(texto)
        return Fantasma(
            datetime.fromisoformat(d["inicio"]),
            float(d["importe"]),
            float(d["caja"]),
            d.get("btc_inicio"),
            {c: Hueco(float(q), float(i)) for c, (q, i) in d["posiciones"].items()},
            int(d.get("operaciones", 0)),
        )
    except (ValueError, KeyError, TypeError):
        return None
