"""Los botones que van debajo de cada aviso."""

from .alerts import ALTO, SIMBOLOS, Alert, _num
from .puntuales import CARTERA, Puntual
from .tendencias import Tendencia

# Telegram no deja meter mas de 64 bytes en cada boton.
MAX_DATOS = 64

# Con mas filas el aviso se queda en segundo plano detras de tanto boton.
MAX_CRIPTOS = 3

CALLAR = ("🔕 Callar 1 h", "/mute 1h")

# Cuando salta una /alerta, la siguiente se ofrece un 5 % mas alla.
OTRA = 5

VOLVER = ("🔔 Volver a avisar", "/unmute")

# Lo que mas se usa: un rato, una tarde y hasta que te levantas.
TIEMPOS = [
    ("1 h", "/mute 1h"),
    ("4 h", "/mute 4h"),
    ("🌙 Hasta las 8:00", "/mute hasta 8:00"),
]

# En el movil, con mas de dos por fila los nombres se cortan.
POR_FILA = 2

# Con mas, el mensaje se convierte en un muro de botones. El resto, con /quitar.
MAX_ALERTAS = 10


def para_avisos(avisos: list[Alert], currency: str) -> list[list[tuple[str, str]]]:
    """Filas de (texto, comando). Pulsar un boton es como escribir el comando."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    # Si una cripto sale dos veces (nivel y brusco), la primera manda.
    primeros, vistas = [], set()
    for a in avisos:
        if a.coin_id not in vistas:
            vistas.add(a.coin_id)
            primeros.append(a)
    solo_una = len(primeros) == 1

    filas = []
    for a in primeros[:MAX_CRIPTOS]:
        nombre = a.coin_id.replace("-", " ").title()
        # Con coma: puntuales.numero leeria "1.234" como 1234.
        precio = repr(a.threshold).replace(".", ",")
        grafica = "/cartera" if a.coin_id == CARTERA else f"/historico {a.coin_id}"
        fila = [
            ("📈 Gráfica" if solo_una else f"📈 {nombre}", grafica),
            (
                f"🎯 Si vuelve a {simbolo}{_num(a.threshold)}",
                f"/alerta {a.coin_id} {precio}",
            ),
        ]
        filas.append([b for b in fila if _cabe(b)])
        if a.puntual:
            filas.append([b for b in [_otra(a, nombre, solo_una)] if _cabe(b)])

    filas.append([CALLAR])
    return [f for f in filas if f]


def _otra(a: Alert, nombre: str, solo_una: bool) -> tuple[str, str]:
    """Otra /alerta un poco mas alla, en la misma direccion en que ha saltado."""
    signo = "+" if a.estado == ALTO else "-"
    texto = f"🔁 Otra a {signo}{OTRA}%" if solo_una else f"🔁 {nombre} {signo}{OTRA}%"
    return texto, f"/alerta {a.coin_id} {signo}{OTRA}%"


def _cabe(boton: tuple[str, str]) -> bool:
    return len(boton[1].encode()) <= MAX_DATOS


def actualizar(comando: str) -> list[list[tuple[str, str]]]:
    """Un solo boton que repite el comando, para ver los precios de ahora."""
    return [[("🔄 Actualizar", comando)]]


def para_tendencias(lista: list[Tendencia]) -> list[list[tuple[str, str]]]:
    """Un boton por cripto: /alerta a secas dice el precio y pone un ejemplo."""
    botones = [
        (f"🎯 {t.simbolo or t.nombre}", f"/alerta {t.coin_id}")
        for t in lista
        if len(f"/alerta {t.coin_id}".encode()) <= MAX_DATOS
    ]
    return [botones[i : i + POR_FILA] for i in range(0, len(botones), POR_FILA)]


def para_alertas(alertas: list[Puntual]) -> list[list[tuple[str, str]]]:
    """Un 🗑 por alerta para /alertas, y al final actualizar y quitarlas todas."""
    botones = []
    for a in alertas[:MAX_ALERTAS]:
        nombre = "Cartera" if a.coin_id == CARTERA else a.coin_id.replace("-", " ")
        botones.append((f"🗑 {a.id} {nombre.title()}", f"/quitar {a.id}"))

    filas = [botones[i : i + POR_FILA] for i in range(0, len(botones), POR_FILA)]
    ultima = actualizar("/alertas")[0]
    if len(alertas) > 1:
        ultima.append(("🗑 Quitar todas", "/quitar todas"))
    filas.append(ultima)
    return filas


def para_mute(ya_callado: bool = False) -> list[list[tuple[str, str]]]:
    """Cuanto tiempo callar; si ya lo estaba, primero el boton para deshacerlo."""
    filas = [TIEMPOS[i : i + POR_FILA] for i in range(0, len(TIEMPOS), POR_FILA)]
    return [[VOLVER], *filas] if ya_callado else filas


def deshacer_mute() -> list[list[tuple[str, str]]]:
    return [[VOLVER]]


def deshacer_movimiento(
    movimiento_id: int, texto: str = "↩️ Deshacer"
) -> list[list[tuple[str, str]]]:
    # Con el numero: si luego apuntas otra, este boton ya no deshace la nueva.
    return [[(texto, f"/deshacer {movimiento_id}")]]
