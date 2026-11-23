"""Los botones que van debajo de cada aviso."""

from datetime import datetime

from . import voto
from .alerts import ALTO, SIMBOLOS, Alert, _num
from .emocion import EMOCIONES
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


def para_avisos(
    avisos: list[Alert], currency: str, ahora: datetime | None = None
) -> list[list[tuple[str, str]]]:
    """Filas de (texto, comando). Pulsar un boton es como escribir el comando.

    Con ahora, la hora del aviso, lleva también los 👍 y 👎 para /ruido.
    """
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

    if ahora is not None and solo_una and _se_vota(primeros[0]):
        coin_id = primeros[0].coin_id
        votar = [
            ("👍 Me sirve", voto.datos(coin_id, True, ahora)),
            ("👎 Sobraba", voto.datos(coin_id, False, ahora)),
        ]
        if all(_cabe(b) for b in votar):
            filas.append(votar)
    filas.append([CALLAR])
    return [f for f in filas if f]


def _se_vota(a: Alert) -> bool:
    # Solo los de /vigilar, que son los que /ruido sabe afinar. Una /alerta la
    # pediste tú tal cual, y con varias criptos no se sabría a cuál va el voto.
    return (
        not a.puntual
        and a.minutos is None
        and a.extremo_dias is None
        and a.coin_id != CARTERA
    )


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


def para_aleatoria(coin_id: str) -> list[list[tuple[str, str]]]:
    fila = [("🎲 Otra", "/aleatoria")]
    if len(f"/precio {coin_id}".encode()) <= MAX_DATOS:
        fila.append(("📈 Su precio", f"/precio {coin_id}"))
    return [fila]


def para_tendencias(lista: list[Tendencia]) -> list[list[tuple[str, str]]]:
    """Un boton por cripto: /alerta a secas dice el precio y pone un ejemplo."""
    botones = [
        (f"🎯 {t.simbolo or t.nombre}", f"/alerta {t.coin_id}")
        for t in lista
        if len(f"/alerta {t.coin_id}".encode()) <= MAX_DATOS
    ]
    return [botones[i : i + POR_FILA] for i in range(0, len(botones), POR_FILA)]


def para_vigilar(coin_ids: list[str]) -> list[list[tuple[str, str]]]:
    """Un ✖ por cripto para /vigilar, que es como escribir /dejar."""
    # Con una sola no: /dejar no deja quitar la ultima y el boton no haria nada.
    if len(coin_ids) < 2:
        return []
    botones = [
        (f"✖ {c.replace('-', ' ').title()}", f"/dejar {c}")
        for c in coin_ids[:MAX_ALERTAS]
    ]
    botones = [b for b in botones if _cabe(b)]
    return [botones[i : i + POR_FILA] for i in range(0, len(botones), POR_FILA)]


def para_precio(coin_id: str, grafica: bool = False) -> list[list[tuple[str, str]]]:
    """Una /alerta un 5 % arriba o abajo de lo que vale ahora, sin escribirla."""
    fila = [
        (f"🔔 Si sube un {OTRA}%", f"/alerta {coin_id} +{OTRA}%"),
        (f"🔔 Si baja un {OTRA}%", f"/alerta {coin_id} -{OTRA}%"),
    ]
    # Con un id larguísimo no caben: mejor sin botones que con uno a medias.
    filas = [fila] if all(_cabe(b) for b in fila) else []
    # Sin precios guardados /historico no tendria nada que dibujar.
    boton = ("📈 Gráfica", f"/historico {coin_id}")
    if grafica and _cabe(boton):
        filas.append([boton])
    return filas


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


def para_pienso(comando: str, coin_id: str) -> list[list[tuple[str, str]]]:
    """Apuntar la compra al precio de ahora, o dejarlo estar."""
    filas = [
        [("✅ La he comprado", comando)],
        [("❌ Al final no", f"/pienso {coin_id} no")],
    ]
    return [f for f in filas if all(_cabe(b) for b in f)]


def tarjeta_anual(año: int) -> list[list[tuple[str, str]]]:
    return [[("🖼️ En imagen para enseñar", f"/anual {año} tarjeta")]]


def para_tesis(numero: int) -> list[list[tuple[str, str]]]:
    return [
        [("✅ Se cumplió", f"/tesis si {numero}"), ("❌ No", f"/tesis no {numero}")]
    ]


def emociones(movimiento_id: int) -> list[list[tuple[str, str]]]:
    """Con qué ánimo la has hecho: un toque y queda apuntado para /emociones."""
    botones = [
        (f"{icono} {nombre}", f"/emocion {movimiento_id} {clave}")
        for clave, (icono, nombre) in EMOCIONES.items()
    ]
    # De tres en tres: con los cinco en una fila no se leen en el móvil.
    return [botones[:3], botones[3:]]


def para_recordatorio(comando: str, coin_id: str) -> list[list[tuple[str, str]]]:
    """Apuntar la compra con lo que sale al precio del aviso, o dejar de recordarla."""
    # Si el precio al final es otro, se deshace y se escribe a mano.
    filas = [
        [("✅ Ya la he hecho", comando)],
        [("🔕 No recordar más", f"/recordar {coin_id} no")],
    ]
    return [f for f in filas if all(_cabe(b) for b in f)]
