"""Entiende los comandos que le escribes al bot por Telegram."""

import difflib
import html
from dataclasses import dataclass

from . import simbolos

# Lo que sale en el menu de Telegram al escribir "/".
COMANDOS = {
    "status": "Cómo van tus criptos ahora",
    "hoy": "Cómo van desde las 00:00, no en 24 h (ej: /hoy o /hoy btc eth)",
    "resumen": "El resumen del día sin esperar, con el índice de miedo",
    "horario": "A qué hora te mando el resumen (ej: /horario 8:30 o /horario no)",
    "precio": "Lo que vale una cripto, varias o, a secas, las que vigilo",
    "ath": "El máximo y el mínimo histórico (ej: /ath bitcoin)",
    "cartera": "Cuánto vale lo que tienes, con gráfica (ej: /cartera 30d)",
    "reparto": "Qué parte de tu cartera es cada cripto, con gráfica",
    "semana": "Cómo le ha ido a tu cartera esta semana, o a una (ej: /semana btc)",
    "compra": "Apuntar una compra en la cartera (ej: /compra bitcoin 0.01 600)",
    "venta": "Apuntar una venta (ej: /venta bitcoin 0.005 350 o todo)",
    "movimientos": "Tus últimas compras y ventas (ej: /movimientos btc)",
    "ganancias": "Lo que has ganado o perdido con lo que ya vendiste",
    "primera": "Tu primera compra y cuánto ha cambiado desde entonces",
    "deshacer": "Quitar la última compra o venta que apuntaste",
    "alerta": "Avísame una vez a un precio o un % (ej: /alerta btc 70000 o +10% 7d)",
    "alertas": "Las alertas que tienes puestas",
    "ultimo": "Cuándo te avisó por última vez cada una y cuánto se ha movido",
    "quitar": "Quitar alertas (ej: /quitar 3, /quitar btc o /quitar todas)",
    "historico": "Cómo ha ido una cripto (ej: /historico bitcoin 7d)",
    "media": "Las medias de 7, 30 y 90 días y si está por encima (ej: /media btc)",
    "racha": "Cuántos días seguidos lleva subiendo o bajando (ej: /racha btc)",
    "extremo": "Su mejor y su peor día del tramo (ej: /extremo btc 30d)",
    "verdes": "Cuántos días ha subido y cuántos ha bajado (ej: /verdes btc 30d)",
    "diasemana": "Qué día de la semana suele subir más (ej: /diasemana btc 90d)",
    "horas": "A qué hora suele estar más barata (ej: /horas btc 30d)",
    "rango": "Entre qué precios se ha movido y dónde está hoy (ej: /rango btc 30d)",
    "dia": "A cuánto estaba un día concreto (ej: /dia btc 01/09 o ayer)",
    "cuando": "La última vez que estuvo a un precio (ej: /cuando btc 60000)",
    "redondo": "Cuánto le falta para la siguiente cifra redonda (ej: /redondo btc)",
    "rsi": "Si ha subido o bajado demasiado rápido (ej: /rsi btc)",
    "caida": "Cuánto ha bajado desde el máximo (ej: /caida btc 30d)",
    "sube": "Cuánto ha subido desde el mínimo (ej: /sube btc 30d)",
    "volatilidad": "Cuánto se mueve, para elegir el % (ej: /volatilidad btc 30d)",
    "vigilar": "Ver o cambiar lo que vigilo (ej: /vigilar solana %5)",
    "dejar": "Dejar de vigilar una o varias (ej: /dejar solana o /dejar sol eth)",
    "comparar": "Qué tal les ha ido, de mejor a peor (ej: /comparar btc eth 7d)",
    "correlacion": "Si dos criptos se mueven a la vez (ej: /correlacion btc eth 30d)",
    "ratio": "Cuánto vale una en otra y cómo ha cambiado (ej: /ratio eth btc 30d)",
    "convertir": "Cuánto es en dinero o en cripto (ej: /convertir 0.05 bitcoin)",
    "si": "Cuánto tendrías si hubieras invertido (ej: /si 1000 bitcoin 30d)",
    "dca": "Lo mismo, metiendo un poco cada semana (ej: /dca 50 bitcoin 90d)",
    "objetivo": "Cuánto valdría tu cartera a ese precio (ej: /objetivo btc 100000)",
    "equilibrio": "A qué precio dejas de perder con cada una de tu cartera",
    "doble": "A qué precio doblas lo que metiste en cada una de tu cartera",
    "exportar": "Los precios guardados en un CSV (ej: /exportar bitcoin 30d)",
    "mercado": "Lo que vale todo el mercado y cuánto es de Bitcoin",
    "halving": "Cuánto falta para el próximo halving de Bitcoin",
    "cumple": "Los años de Bitcoin y cuánto falta para su cumpleaños",
    "whitepaper": "Los años del whitepaper de Satoshi y cuánto falta para cumplir",
    "merge": "Los años desde que Ethereum dejó la minería",
    "pizza": "Lo que valdrían hoy los 10.000 BTC de las pizzas de 2010",
    "millonario": "Cuánto necesitas para tener un millón (ej: /millonario eth)",
    "sat": "Lo que vale un satoshi y cuántos te dan 1, 10 y 100",
    "lambo": "Cuántos Lamborghinis te da tu cartera",
    "cafe": "Cuántos cafés te da tu cartera",
    "sueldo": "Cuántos meses de salario mínimo es tu cartera",
    "gasolina": "Cuántos litros de gasolina te da tu cartera",
    "bigmac": "Cuántos Big Mac te da tu cartera",
    "tendencias": "Las criptos que más se buscan hoy",
    "top": "Las 5 que más suben y las 5 que más bajan hoy",
    "aleatoria": "Una de las 100 más grandes al azar, para descubrir alguna",
    "caraocruz": "¿Compro o vendo? Una moneda al aire (ej: /caraocruz btc)",
    "frase": "Una frase famosa del mundo cripto, al azar",
    "glosario": "Qué significa hodl, fomo, dca... (ej: /glosario fomo)",
    "miedo": "El índice de miedo y codicia del mercado",
    "buscar": "Encuentra el id de una cripto (ej: /buscar btc)",
    "copia": "Lo que vigilo y tu cartera, listo para pegar en el .env",
    "ajustes": "Lo que tienes puesto: moneda, horas tranquilas, avisos...",
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
    "range": "rango",
    "streak": "racha",
    "rojos": "verdes",
    "mejor": "extremo",
    "peor": "extremo",
    "drawdown": "caida",
    "sobrecompra": "rsi",
    "cuándo": "cuando",
    "when": "cuando",
    "día": "dia",
    "fecha": "dia",
    "backup": "copia",
    "tarta": "reparto",
    "pesos": "reparto",
    "correlación": "correlacion",
    "correlation": "correlacion",
    "env": "copia",
    "caída": "caida",
    "subida": "sube",
    "today": "hoy",
    "hours": "horas",
    "weekday": "diasemana",
    "breakeven": "equilibrio",
    "x2": "doble",
    "first": "primera",
    "café": "cafe",
    "coffee": "cafe",
    "salario": "sueldo",
    "smi": "sueldo",
    "salary": "sueldo",
    "gasoil": "gasolina",
    "gas": "gasolina",
    "burger": "bigmac",
    "hamburguesa": "bigmac",
    "ganancia": "ganancias",
    "beneficios": "ganancias",
    # /maximo ya es /ath; el mínimo del tramo sale en lo primero de /sube.
    "minimo": "sube",
    "mínimo": "sube",
    "average": "media",
    "ranking": "comparar",
    "global": "mercado",
    "máximo": "ath",
    "silencio": "mute",
    "callar": "mute",
    "redondos": "redondo",
    "round": "redondo",
    "config": "ajustes",
    "settings": "ajustes",
    "random": "aleatoria",
    "azar": "aleatoria",
    "moneda": "caraocruz",
    "flip": "caraocruz",
    "cita": "frase",
    "quote": "frase",
    # Sin "hodl": se parece tanto a "hola" que a un saludo le sugería /glosario.
    "glossary": "glosario",
    "diccionario": "glosario",
    "sats": "sat",
    "satoshi": "sat",
    "summary": "resumen",
    "schedule": "horario",
    "week": "semana",
    "transactions": "movimientos",
    "profit": "ganancias",
    "pnl": "ganancias",
    "remove": "quitar",
    "delete": "quitar",
    "unwatch": "dejar",
    "green": "verdes",
    "day": "dia",
    "date": "dia",
    "whatif": "si",
    "allocation": "reparto",
    "birthday": "cumple",
    "millionaire": "millonario",
    "usage": "consultas",
    "quota": "consultas",
    "último": "ultimo",
    "last": "ultimo",
    "ping": "bot",
    "uptime": "bot",
    "millon": "millonario",
    "millón": "millonario",
    "cumpleaños": "cumple",
    "edad": "cumple",
    "paper": "whitepaper",
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
        ("/precio btc usd", "en otra moneda: eur, usd o gbp"),
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
        ("/quitar bitcoin", "todas las de esa cripto"),
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
        ("/cartera usd", "lo que vale en dólares, sin lo que ganas"),
    ],
    "compra": [
        ("/compra bitcoin 0.01 600", "0,01 por 600 € en total"),
        ("/compra bitcoin 0.01 @60000", "con el precio de cada una"),
    ],
    "venta": [
        ("/venta bitcoin 0.005 350", "una parte, por 350 € en total"),
        ("/venta bitcoin 0.005 @70000", "con el precio de cada una"),
        ("/venta bitcoin 0.005", "sin precio, al de ahora"),
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
    "correlacion": [
        ("/correlacion btc eth", "si suben y bajan a la vez, en 30 días"),
        ("/correlacion btc sol 90d", "del tramo que digas"),
        ("/correlacion", "a secas, las dos primeras que vigilo"),
    ],
    "convertir": [
        ("/convertir 0.05 bitcoin", "cuánto es en dinero"),
        ("/convertir 500 eur solana", "cuánta compras con 500 €"),
        ("/convertir 1 eth btc", "de una cripto a otra"),
        ("/convertir 100000 sats", "en satoshis, también 50 eur sats"),
    ],
    "si": [
        ("/si 1000 bitcoin 30d", "si hubieras metido 1.000 € hace 30 días"),
        ("/si 1000 btc", "sin tramo, 30 días"),
    ],
    "dca": [
        ("/dca 50 bitcoin", "50 € cada semana durante 90 días"),
        ("/dca 50 bitcoin diario 30d", "también diario o mensual"),
    ],
    "media": [
        ("/media bitcoin", "la de 7, 30 y 90 días, y si está por encima o debajo"),
        ("/media bitcoin 14d", "solo la de esos días"),
        ("/media", "a secas, la primera que vigilo"),
    ],
    "racha": [
        ("/racha bitcoin", "cuántos días seguidos lleva subiendo o bajando"),
        ("/racha", "a secas, la primera que vigilo"),
    ],
    "extremo": [
        ("/extremo bitcoin", "el día que más subió y el que más bajó en 30 días"),
        ("/extremo bitcoin 7d", "del tramo que digas"),
        ("/extremo", "a secas, la primera que vigilo"),
    ],
    "verdes": [
        ("/verdes bitcoin", "cuántos días subió y cuántos bajó en 30 días"),
        ("/verdes bitcoin 7d", "del tramo que digas"),
        ("/verdes", "a secas, la primera que vigilo"),
    ],
    "diasemana": [
        ("/diasemana bitcoin", "lo que cambia de media cada día en 90 días"),
        ("/diasemana bitcoin 30d", "del tramo que digas"),
        ("/diasemana", "a secas, la primera que vigilo"),
    ],
    "horas": [
        ("/horas bitcoin", "a qué hora suele estar más barata y más cara en 30 días"),
        ("/horas bitcoin 7d", "del tramo que digas"),
        ("/horas", "a secas, la primera que vigilo"),
    ],
    "equilibrio": [
        ("/equilibrio", "a qué precio te salió cada una y cuánto le falta"),
    ],
    "hoy": [
        ("/hoy", "cómo van las que vigilo desde las 00:00"),
        ("/hoy btc eth", "solo esas"),
    ],
    "ratio": [
        ("/ratio eth btc", "cuánto bitcoin vale un ethereum y cómo ha ido en 30 días"),
        ("/ratio eth btc 7d", "del tramo que digas"),
        ("/ratio", "a secas, las dos primeras que vigilo"),
    ],
    "rango": [
        ("/rango bitcoin", "máximo, mínimo y media de los últimos 7 días"),
        ("/rango bitcoin 30d", "del tramo que digas"),
        ("/rango", "a secas, la primera que vigilo"),
    ],
    "dia": [
        ("/dia bitcoin 01/09", "cómo cerró ese día, con su máximo y su mínimo"),
        ("/dia bitcoin ayer", "también hoy, ayer y anteayer"),
        ("/dia 01/09/2025", "con año; sin cripto, la primera que vigilo"),
    ],
    "rsi": [
        ("/rsi bitcoin", "el RSI de 14 días: por encima de 70 sobrecomprada"),
        ("/rsi", "a secas, la primera que vigilo"),
    ],
    "caida": [
        ("/caida bitcoin", "cuánto ha bajado desde el máximo de 30 días"),
        ("/caida bitcoin 7d", "del tramo que digas"),
        ("/caida", "a secas, la primera que vigilo"),
    ],
    "sube": [
        ("/sube bitcoin", "cuánto ha subido desde el mínimo de 30 días"),
        ("/sube bitcoin 7d", "del tramo que digas"),
        ("/sube", "a secas, la primera que vigilo"),
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
