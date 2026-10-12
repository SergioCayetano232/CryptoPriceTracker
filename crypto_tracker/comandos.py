"""Entiende los comandos que le escribes al bot por Telegram."""

import difflib
import html
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
    "objetivo": "Cuánto valdría tu cartera a ese precio (ej: /objetivo btc 100000)",
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
    "target": "objetivo",
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

AYUDA = (
    "🤖 <b>Esto es lo que sé hacer</b>\n\n"
    + "\n".join(f"/{nombre} — {texto}" for nombre, texto in COMANDOS.items())
    + "\n\nCon ejemplos de uno: /ayuda alerta"
)

# Para /ayuda alerta. Solo los que tienen varias formas; el resto con su linea basta.
EJEMPLOS = {
    "precio": [
        ("/precio solana", "lo que vale, y cómo va en 1 h, 24 h y 7 días"),
        ("/precio btc eth sol", "varias a la vez (hasta 10)"),
        ("/precio", "a secas, las que vigilo"),
        ("btc", "sin barra, lo mismo"),
    ],
    "alerta": [
        ("/alerta bitcoin 70000", "te aviso una vez cuando llegue"),
        ("/alerta bitcoin +10%", "cuando suba un 10% desde ahora"),
        ("/alerta bitcoin 70000 7d", "si en 7 días no llega, se borra sola"),
        ("/alerta bitcoin 70000 vender la mitad", "con una nota para el aviso"),
        ("/alerta cartera 5000", "con lo que vale tu cartera entera"),
        ("/alerta bitcoin", "sin precio, te digo a cuánto está"),
    ],
    "quitar": [
        ("/quitar 3", "la número 3 de /alertas"),
        ("/quitar 2 5", "varias"),
        ("/quitar todas", "todas"),
    ],
    "vigilar": [
        ("/vigilar", "lo que vigilo y cómo"),
        ("/vigilar solana %5", "aviso cada vez que se mueva un 5%"),
        ("/vigilar bitcoin 1000", "aviso cada 1.000 de subida o bajada"),
        ("/vigilar bitcoin 55000 75000", "aviso si sale de ese rango"),
    ],
    "cartera": [
        ("/cartera", "cuánto vale, con la gráfica de 7 días"),
        ("/cartera 30d", "con la gráfica del tramo que digas"),
    ],
    "compra": [
        ("/compra bitcoin 0.01 600", "0,01 por 600 € en total"),
        ("/compra bitcoin 0.01 @60000", "con el precio de cada una"),
    ],
    "venta": [
        ("/venta bitcoin 0.005", "una parte"),
        ("/venta bitcoin todo", "la saca de la cartera"),
    ],
    "historico": [
        ("/historico bitcoin", "gráfica de las últimas 24 h"),
        ("/historico bitcoin 7d", "del tramo que digas (12h, 7d, 30d...)"),
        ("/historico", "a secas, la primera que vigilo"),
    ],
    "comparar": [
        ("/comparar btc eth sol 7d", "de la que mejor ha ido a la peor"),
        ("/comparar", "a secas, las que vigilo en 7 días"),
    ],
    "convertir": [
        ("/convertir 0.05 bitcoin", "cuánto es en dinero"),
        ("/convertir 500 eur solana", "cuánta compras con 500 €"),
    ],
    "si": [
        ("/si 1000 bitcoin 30d", "si hubieras metido 1.000 € hace 30 días"),
        ("/si 1000 btc", "sin tramo, 30 días"),
    ],
    "dca": [
        ("/dca 50 bitcoin", "50 € cada semana durante 90 días"),
        ("/dca 50 bitcoin diario 30d", "también diario o mensual"),
    ],
    "objetivo": [
        ("/objetivo bitcoin 100000", "lo que valdría tu cartera si llega a 100.000"),
        ("/objetivo eth 1500", "también vale para ver qué pasa si baja"),
    ],
    "mute": [
        ("/mute", "te pregunto cuánto, con botones"),
        ("/mute 2h", "me callo ese rato"),
        ("/mute hasta 8:00", "hasta esa hora"),
        ("/mute bitcoin 2h", "solo esa, las demás siguen"),
    ],
    "unmute": [
        ("/unmute", "vuelvo a avisar de todo"),
        ("/unmute bitcoin", "solo de esa"),
    ],
    "horario": [
        ("/horario", "a qué hora te mando el resumen"),
        ("/horario 8:30", "cambiarla"),
        ("/horario no", "quitarlo"),
    ],
}

NO_ENTIENDO = "No te entiendo. Escribe /ayuda para ver lo que sé hacer."


def no_entiendo(nombre: str, argumento: str = "") -> str:
    """Si se parece a un comando, lo sugiere con lo que escribiste detras."""
    # Con menos de 0.75 sugeria /vigilar para /bailar y /compra para /borrar.
    parecidos = difflib.get_close_matches(nombre, [*COMANDOS, *ALIAS], n=1, cutoff=0.75)
    if not parecidos:
        return NO_ENTIENDO
    sugerencia = f"/{ALIAS.get(parecidos[0], parecidos[0])} {argumento}".strip()
    return f"No te entiendo. ¿Querías decir {sugerencia}?"


def ayuda(argumento: str = "") -> str:
    """/ayuda a secas, la lista. /ayuda alerta, ese con sus ejemplos."""
    if not argumento.strip():
        return AYUDA

    pedido = argumento.split()[0].lstrip("/").lower()
    nombre = ALIAS.get(pedido, pedido)
    if nombre not in COMANDOS:
        parecidos = difflib.get_close_matches(
            nombre, [*COMANDOS, *ALIAS], n=1, cutoff=0.75
        )
        pedido = html.escape(pedido)
        if parecidos:
            sugerencia = ALIAS.get(parecidos[0], parecidos[0])
            return f"No conozco /{pedido}. ¿Querías decir /ayuda {sugerencia}?"
        return f"No conozco /{pedido}. Con /ayuda te salen todos."

    texto = f"<b>/{nombre}</b> — {COMANDOS[nombre]}"
    if nombre in EJEMPLOS:
        texto += "\n\n" + "\n".join(
            f"<code>{ejemplo}</code> — {que}" for ejemplo, que in EJEMPLOS[nombre]
        )
    return texto


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
