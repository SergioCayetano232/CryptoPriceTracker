"""Entiende los comandos que le escribes al bot por Telegram."""

import difflib
from dataclasses import dataclass

from . import simbolos

# Lo que sale en el menu de Telegram al escribir "/".
COMANDOS = {
    "status": "Cómo van tus criptos ahora",
    "resumen": "El resumen del día sin esperar, con el índice de miedo",
    "horario": "A qué hora te mando el resumen (ej: /horario 8:30 o /horario no)",
    "precio": "Lo que vale una cripto, varias o, a secas, las que vigilo",
    "ath": "El máximo histórico y cuánto le falta (ej: /ath bitcoin)",
    "cartera": "Cuánto vale lo que tienes, con gráfica (ej: /cartera 30d)",
    "semana": "Cómo le ha ido a tu cartera esta semana, sin esperar al domingo",
    "compra": "Apuntar una compra en la cartera (ej: /compra bitcoin 0.01 600)",
    "venta": "Apuntar una venta (ej: /venta bitcoin 0.005 o todo)",
    "movimientos": "Tus últimas compras y ventas",
    "deshacer": "Quitar la última compra o venta que apuntaste",
    "alerta": "Avísame una vez a un precio o un % (ej: /alerta btc 70000 o +10% 7d)",
    "alertas": "Las alertas que tienes puestas",
    "quitar": "Quitar alertas (ej: /quitar 3, /quitar 2 5 o /quitar todas)",
    "historico": "Cómo ha ido una cripto (ej: /historico bitcoin 7d)",
    "volatilidad": "Cuánto se mueve, para elegir el % (ej: /volatilidad btc 30d)",
    "vigilar": "Ver o cambiar lo que vigilo (ej: /vigilar solana %5)",
    "dejar": "Dejar de vigilar una o varias (ej: /dejar solana o /dejar sol eth)",
    "comparar": "Qué tal les ha ido, de mejor a peor (ej: /comparar btc eth 7d)",
    "convertir": "Cuánto es en dinero o en cripto (ej: /convertir 0.05 bitcoin)",
    "si": "Cuánto tendrías si hubieras invertido (ej: /si 1000 bitcoin 30d)",
    "dca": "Lo mismo, metiendo un poco cada semana (ej: /dca 50 bitcoin 90d)",
    "exportar": "Los precios guardados en un CSV (ej: /exportar bitcoin 30d)",
    "mercado": "Lo que vale todo el mercado y cuánto es de Bitcoin",
    "tendencias": "Las criptos que más se buscan hoy",
    "top": "Las 5 que más suben y las 5 que más bajan hoy",
    "miedo": "El índice de miedo y codicia del mercado",
    "buscar": "Encuentra el id de una cripto (ej: /buscar btc)",
    "consultas": "Cuántas consultas a CoinGecko llevas este mes",
    "mute": "Callar los avisos un rato (ej: /mute 2h o /mute bitcoin hasta 8:00)",
    "unmute": "Volver a avisar",
    "bot": "Si sigo funcionando: desde cuándo y el último ciclo",
    "ayuda": "Lo que sé hacer",
}

# /start lo manda Telegram solo la primera vez que abres el chat.
ALIAS = {
    "start": "ayuda",
    "help": "ayuda",
    "history": "historico",
    "search": "buscar",
    "price": "precio",
    "convert": "convertir",
    "export": "exportar",
    "portfolio": "cartera",
    "comprar": "compra",
    "buy": "compra",
    "vender": "venta",
    "sell": "venta",
    "historial": "movimientos",
    "semanal": "semana",
    "undo": "deshacer",
    "alert": "alerta",
    "alerts": "alertas",
    "watch": "vigilar",
    "estado": "status",
    "p": "precio",
    "maximo": "ath",
    "trending": "tendencias",
    "moda": "tendencias",
    "suben": "top",
    "bajan": "top",
    "codicia": "miedo",
    "fear": "miedo",
    "market": "mercado",
    "compare": "comparar",
    "volatility": "volatilidad",
    "ranking": "comparar",
    "global": "mercado",
    "máximo": "ath",
    "silencio": "mute",
    "callar": "mute",
}

AYUDA = "🤖 <b>Esto es lo que sé hacer</b>\n\n" + "\n".join(
    f"/{nombre} — {texto}" for nombre, texto in COMANDOS.items()
)

NO_ENTIENDO = "No te entiendo. Escribe /ayuda para ver lo que sé hacer."


def no_entiendo(nombre: str, argumento: str = "") -> str:
    """Si se parece a un comando, lo sugiere con lo que escribiste detras."""
    # Con menos de 0.75 sugeria /vigilar para /bailar y /compra para /borrar.
    parecidos = difflib.get_close_matches(nombre, [*COMANDOS, *ALIAS], n=1, cutoff=0.75)
    if not parecidos:
        return NO_ENTIENDO
    sugerencia = f"/{ALIAS.get(parecidos[0], parecidos[0])} {argumento}".strip()
    return f"No te entiendo. ¿Querías decir {sugerencia}?"


@dataclass(frozen=True)
class Foto:
    """Una respuesta con imagen. texto es lo que se manda si la imagen no pasa."""

    png: bytes
    pie: str
    texto: str
    botones: list[list[tuple[str, str]]] | None = None


def interpretar(texto: str) -> tuple[str, str] | None:
    """'/mute@MiBot 2h' -> ('mute', '2h'). None si no es un comando."""
    partes = texto.strip().split(maxsplit=1)
    if not partes:
        return None
    if not partes[0].startswith("/"):
        return ("precio", texto.strip()) if _son_criptos(texto) else None

    # En los grupos Telegram le pega el nombre del bot: /status@MiBot
    nombre = partes[0][1:].split("@")[0].lower()
    argumento = partes[1].strip() if len(partes) > 1 else ""
    return ALIAS.get(nombre, nombre), argumento


def _son_criptos(texto: str) -> bool:
    """'btc' o 'btc eth' a secas, que es lo que mas se escribe."""
    # Solo las conocidas: con cualquier palabra, un "hola" acabaria en /precio hola.
    conocidas = {*simbolos.IDS, *simbolos.IDS.values()}
    palabras = texto.lower().replace(",", " ").split()
    return 0 < len(palabras) <= simbolos.MAX_VARIAS and all(
        p in conocidas for p in palabras
    )


@dataclass(frozen=True)
class Archivo:
    """Una respuesta con un adjunto. texto es lo que se manda si no pasa."""

    contenido: bytes
    nombre: str
    pie: str
    texto: str


@dataclass(frozen=True)
class ConBotones:
    """Una respuesta de texto con botones debajo, filas de (texto, comando)."""

    texto: str
    botones: list[list[tuple[str, str]]]
