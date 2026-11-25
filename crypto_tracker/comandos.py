"""Entiende los comandos que le escribes al bot por Telegram."""

import difflib
import html
from dataclasses import dataclass

from . import equivale, lenguaje, simbolos, temas

# Lo que sale en el menu de Telegram al escribir "/".
COMANDOS = {
    "status": "Cómo van tus criptos ahora",
    "hoy": "Cómo van desde las 00:00, no en 24 h (ej: /hoy o /hoy btc eth)",
    "resumen": "El resumen del día sin esperar, con el índice de miedo",
    "horario": "A qué hora te mando el resumen (ej: /horario 8:30 o /horario no)",
    "dormir": "Horas en que los avisos no suenan (ej: /dormir 23-8 o /dormir no)",
    "envivo": "Un mensaje fijado arriba que se actualiza solo (/envivo no lo quita)",
    "precio": "Lo que vale una cripto, varias o, a secas, las que vigilo",
    "ath": "El máximo y el mínimo histórico (ej: /ath bitcoin)",
    "cartera": "Cuánto vale lo que tienes, con gráfica (ej: /cartera 30d)",
    "reparto": "Qué parte de tu cartera es cada cripto, con gráfica",
    "tarjeta": "Una imagen de tu cartera para enseñar, solo con %",
    "riesgo": "Cuánto depende tu cartera de una cripto y cuánto se mueve",
    "futuro": "Entre qué cifras puede estar tu cartera (ej: /futuro 30d)",
    "sharpe": "Cuánto gana tu cartera para lo que se mueve (ej: /sharpe 90d)",
    "rebalanceo": "Qué mover para un reparto (ej: /rebalanceo btc 60 eth 40)",
    "ideal": "Tu reparto ideal, y aviso si te alejas (ej: /ideal btc 60 eth 40)",
    "semana": "Cómo le ha ido a tu cartera esta semana, o a una (ej: /semana btc)",
    "mes": "Cómo va tu cartera desde el día 1 del mes",
    "anual": "Cómo va tu cartera este año, o tu resumen de uno (ej: /anual 2025)",
    "compra": "Apuntar una compra en la cartera (ej: /compra bitcoin 0.01 600)",
    "venta": "Apuntar una venta (ej: /venta bitcoin 0.005 350 o todo)",
    "importar": "Apuntar tus compras y ventas del CSV de Binance o Kraken",
    "binance": "Lo que tienes de verdad en Binance contra lo apuntado",
    "recompensa": "Apuntar staking o un airdrop (ej: /recompensa eth 0.02)",
    "movimientos": "Tus últimas compras y ventas (ej: /movimientos btc)",
    "compras": "Tu mejor y tu peor compra (ej: /compras o /compras btc)",
    "timing": "Si aciertas el momento de comprar o da igual (ej: /timing btc)",
    "ganancias": "Lo que has ganado o perdido con lo que ya vendiste",
    "arrepentido": "Lo que valdría hoy lo que vendiste, ¿hiciste bien?",
    "rentabilidad": "Lo que ganas al año, contando cuándo metiste cada euro",
    "impuestos": "Lo que le tocaría a Hacienda de lo que ganaste vendiendo",
    "informe": "Tu año fiscal en un PDF, para ti o para el gestor (ej: /informe 2025)",
    "comisiones": "Lo que llevas pagado en comisiones (ej: /comisiones 2026)",
    "sivendo": "Lo que ganarías y pagarías antes de vender (ej: /sivendo btc 0.5)",
    "permuta": "Lo que pagas a Hacienda al cambiar una cripto por otra",
    "compensar": "Qué vender en pérdidas para pagar menos a Hacienda este año",
    "modelo721": "Si te toca declarar las criptos que tienes en exchanges de fuera",
    "primera": "Tu primera compra y cuánto ha cambiado desde entonces",
    "pelotazo": "Tu mejor compra y la peor, por lo que han subido o bajado",
    "apodo": "Un mote para ti según cómo llevas la cartera",
    "hodl": "Cuántos días llevas sin vender cada cripto de tu cartera",
    "record": "Lo máximo que ha valido tu cartera y cuánto le falta para volver",
    "vsbtc": "Tu cartera contra haber metido lo mismo en bitcoin",
    "vsbolsa": "Tu cartera contra la bolsa (ej: /vsbolsa o /vsbolsa world)",
    "deposito": "Tu cartera contra un depósito (ej: /deposito 3%)",
    "inflacion": "Si tu cartera le gana a la subida de precios en España",
    "recordar": "Avísame cada semana de mi compra (ej: /recordar lunes 50 btc)",
    "cada": "Mándame un comando solo (ej: /cada viernes 20:00 /cartera)",
    "rezagada": "Avísame si una va peor que otra en 7 días (ej: /rezagada eth btc 10)",
    "juntas": "Avísame si dos que van a la vez se separan (ej: /juntas btc eth)",
    "pienso": "Antes de comprar, 24 h para pensarlo (ej: /pienso btc 500)",
    "tesis": "Por qué compras, y al mes vemos si acertaste (ej: /tesis sol el ETF)",
    "fantasma": "Una cartera de mentira para probar (ej: /fantasma compra btc 200)",
    "herencia": "Lo que tienes y dónde, para tu familia, sin claves",
    "emociones": "Con qué ánimo compras y vendes, y qué te sale de cada uno",
    "emocion": "Apuntar con qué ánimo hiciste un movimiento (ej: /emocion 12 miedo)",
    "encuesta": "Cada lunes, una encuesta con dónde acabará el domingo",
    "liga": "Quién acierta más con /prediccion, entre tú y tus invitados",
    "prediccion": "A cuánto estará el domingo, y tu marcador (ej: /prediccion btc 70k)",
    "deshacer": "Quitar la última compra o venta que apuntaste",
    "corregir": "Cambiar una compra o venta antigua (ej: /corregir 12 importe 700)",
    "alerta": "Avísame una vez a un precio o un % (ej: /alerta btc 70000 o +10% 7d)",
    "escalera": "Vender por tramos al subir, o comprar al bajar (ej: /ayuda escalera)",
    "stop": "Avísame al perder o ganar un % sobre lo que pagué (ej: /stop eth -15%)",
    "alertas": "Las alertas que tienes puestas",
    "ultimo": "Cuándo te avisó por última vez cada una y cuánto se ha movido",
    "quitar": "Quitar alertas (ej: /quitar 3, /quitar btc o /quitar todas)",
    "historico": "Cómo ha ido una cripto (ej: /historico bitcoin 7d)",
    "media": "Las medias de 7, 30 y 90 días y si está por encima (ej: /media btc)",
    "racha": "Cuántos días seguidos lleva subiendo o bajando (ej: /racha btc)",
    "extremo": "Su mejor y su peor día del tramo (ej: /extremo btc 30d)",
    "calendario": "El mes día a día, en verde o en rojo (ej: /calendario btc)",
    "verdes": "Cuántos días ha subido y cuántos ha bajado (ej: /verdes btc 30d)",
    "diasemana": "Qué día de la semana suele subir más (ej: /diasemana btc 90d)",
    "diames": "Qué día del mes suele salir más barato (ej: /diames btc)",
    "estacional": "Qué meses del año suele subir o bajar (ej: /estacional btc)",
    "mayer": "Si bitcoin está caro o barato frente a su media de 200 días",
    "arcoiris": "La gráfica arcoíris de bitcoin: en qué franja está",
    "suelo": "Bitcoin frente a su media de 200 semanas, el suelo de cada ciclo",
    "picycle": "Si bitcoin está cerca de su techo según el Pi Cycle Top",
    "ahr999": "Si con bitcoin toca comprar fuerte, hacer DCA o esperar",
    "paciencia": "Cuántas veces salía bien comprar y aguantar (ej: /paciencia eth)",
    "cme": "El hueco del fin de semana en los futuros del CME y si se ha cerrado",
    "dvol": "Lo que las opciones esperan que se mueva bitcoin (ej: /dvol eth)",
    "maxpain": "Las opciones que vencen el viernes y su max pain (ej: /maxpain eth)",
    "horas": "A qué hora suele estar más barata (ej: /horas btc 30d)",
    "rango": "Entre qué precios se ha movido y dónde está hoy (ej: /rango btc 30d)",
    "soporte": "Dónde ha girado varias veces arriba y abajo (ej: /soporte btc)",
    "dia": "A cuánto estaba un día concreto (ej: /dia btc 01/09 o ayer)",
    "cuando": "La última vez que estuvo a un precio (ej: /cuando btc 60000)",
    "redondo": "Cuánto le falta para la siguiente cifra redonda (ej: /redondo btc)",
    "semaforo": "Una luz con lo que dicen todos los indicadores (ej: /semaforo btc)",
    "rsi": "Si ha subido o bajado demasiado rápido (ej: /rsi btc)",
    "bollinger": "Si se ha salido de su banda normal (ej: /bollinger btc)",
    "macd": "Si coge o pierde empuje, con el MACD (ej: /macd bitcoin)",
    "estocastico": "Si está cerca del techo o del suelo de 14 días (ej: /stoch btc)",
    "tormenta": "Si alguna está mucho más quieta de lo normal (ej: /tormenta btc)",
    "fibonacci": "Dónde podría frenar el precio (ej: /fibonacci btc 90d)",
    "caida": "Cuánto ha bajado desde el máximo (ej: /caida btc 30d)",
    "backtest": "Vender al +% y recomprar al -%, contra no tocar (ej: /backtest btc)",
    "sube": "Cuánto ha subido desde el mínimo (ej: /sube btc 30d)",
    "volatilidad": "Cuánto se mueve, para elegir el % (ej: /volatilidad btc 30d)",
    "ruido": "Cuántos avisos fueron en falso y un % mejor (ej: /ruido btc 30d)",
    "voto": "Si un aviso te sirvió: va con los 👍 👎 de debajo, no escrito",
    "vigilar": "Ver o cambiar lo que vigilo (ej: /vigilar solana %5)",
    "dejar": "Dejar de vigilar una o varias (ej: /dejar solana o /dejar sol eth)",
    "comparar": "Qué tal les ha ido, de mejor a peor (ej: /comparar btc eth 7d)",
    "quieta": "La que menos se ha movido en 24 h de las que vigilo",
    "correlacion": "Si dos criptos se mueven a la vez (ej: /correlacion btc eth 30d)",
    "ratio": "Cuánto vale una en otra y cómo ha cambiado (ej: /ratio eth btc 30d)",
    "convertir": "Cuánto es en dinero o en cripto (ej: /convertir 0.05 bitcoin)",
    "si": "Cuánto tendrías si hubieras invertido (ej: /si 1000 bitcoin 30d)",
    "dca": "Lo mismo, metiendo un poco cada semana (ej: /dca 50 bitcoin 90d)",
    "objetivo": "Cuánto valdría tu cartera a ese precio (ej: /objetivo btc 100000)",
    "promediar": "Cuánto comprar para bajar tu precio medio (ej: /promediar btc 50000)",
    "posicion": "Cuánto meter según lo que aceptas perder (ej: /posicion 1000 2% -10%)",
    "limite": "Lo que te permites comprar al mes (ej: /limite 300)",
    "apy": "Cuánta cripto tendrías en staking a un % al año (ej: /apy eth 4%)",
    "plan": "Cuánto tardas en llegar a una cifra (ej: /plan 10000 50 semanal)",
    "meta": "Cuánto le falta a tu cartera para una cifra (ej: /meta 10000)",
    "equilibrio": "A qué precio dejas de perder con cada una de tu cartera",
    "doble": "A qué precio doblas lo que metiste en cada una de tu cartera",
    "mitad": "A qué precio pierdes la mitad de lo que metiste en cada una",
    "exportar": "Precios o tus compras en CSV (ej: /exportar btc 30d o movimientos)",
    "rellenar": "Bajar los precios pasados que no tengo (ej: /rellenar btc 90d)",
    "backup": "Te mando la base de datos entera, por si se muere el servidor",
    "mercado": "Lo que vale todo el mercado y cuánto es de Bitcoin",
    "dominancia": "Si el dinero se va a las altcoins o vuelve a bitcoin",
    "halving": "Cuánto falta para el próximo halving de Bitcoin",
    "cumple": "Los años de Bitcoin y cuánto falta para su cumpleaños",
    "whitepaper": "Los años del whitepaper de Satoshi y cuánto falta para cumplir",
    "merge": "Los años desde que Ethereum dejó la minería",
    "ethereum": "Los años de Ethereum y cuánto falta para su cumpleaños",
    "adios": "El tiempo que lleva Satoshi sin aparecer",
    "pizza": "Lo que valdrían hoy los 10.000 BTC de las pizzas de 2010",
    "mundo": "Lo que le tocaría a cada persona si se repartieran todos los bitcoin",
    "millonario": "Cuánto necesitas para tener un millón (ej: /millonario eth)",
    "sat": "Lo que vale un satoshi y cuántos te dan 1, 10 y 100",
    "equivale": "Tu cartera en cafés, cañas, iPhones... (ej: /equivale kebab)",
    "lambo": "Cuántos Lamborghinis te da tu cartera",
    "enletras": "Lo que vale tu cartera, escrito en letras como en un cheque",
    "ballena": "Qué bicho eres según tus bitcoin: gamba, pulpo, tiburón, ballena…",
    "cafe": "Cuántos cafés te da tu cartera",
    "sueldo": "Cuántos meses de salario mínimo es tu cartera",
    "gasolina": "Cuántos litros de gasolina te da tu cartera",
    "bigmac": "Cuántos Big Mac te da tu cartera",
    "iphone": "Cuántos iPhone te da tu cartera",
    "alquiler": "Cuántos meses de alquiler te paga tu cartera",
    "oro": "Cuántos gramos de oro te da tu cartera",
    "netflix": "Cuántos meses de Netflix te paga tu cartera",
    "ps5": "Cuántas PS5 te da tu cartera",
    "tesla": "Cuántos Tesla te da tu cartera",
    "spotify": "Cuántos meses de Spotify te paga tu cartera",
    "cana": "Cuántas cañas te da tu cartera",
    "switch": "Cuántas Switch 2 te da tu cartera",
    "cine": "Cuántas entradas de cine te da tu cartera",
    "gimnasio": "Cuántos meses de gimnasio te paga tu cartera",
    "vuelo": "Cuántos viajes a Nueva York te da tu cartera",
    "super": "Cuántos carros de la compra te da tu cartera",
    "kebab": "Cuántos kebabs te da tu cartera",
    "metro": "Cuántos meses de abono de transporte te paga tu cartera",
    "luz": "Cuántos meses de factura de la luz te paga tu cartera",
    "libro": "Cuántos libros te da tu cartera",
    "concierto": "Cuántas entradas de concierto te da tu cartera",
    "airpods": "Cuántos AirPods Pro te da tu cartera",
    "zapatillas": "Cuántos pares de zapatillas te da tu cartera",
    "ave": "Cuántos viajes en AVE a Barcelona te da tu cartera",
    "menu": "Cuántos menús del día te da tu cartera",
    "hotel": "Cuántas noches de hotel te da tu cartera",
    "peluqueria": "Cuántos cortes de pelo te da tu cartera",
    "macbook": "Cuántos MacBook Air te da tu cartera",
    "bici": "Cuántas bicis de carretera te da tu cartera",
    "churros": "Cuántos chocolates con churros te da tu cartera",
    "loteria": "Cuántos décimos de Navidad te da tu cartera",
    "piso": "Cuántos metros cuadrados de piso en Madrid te da tu cartera",
    "futbol": "Cuántas entradas de fútbol te da tu cartera",
    "taxi": "Cuántos taxis al aeropuerto te da tu cartera",
    "tortilla": "Cuántos pinchos de tortilla te da tu cartera",
    "videojuego": "Cuántos videojuegos nuevos te da tu cartera",
    "sofa": "Cuántos sofás te da tu cartera",
    "coche": "Cuántos coches nuevos te da tu cartera",
    "boda": "Cuántas bodas te da tu cartera",
    "jamon": "Cuántos jamones ibéricos te da tu cartera",
    "rolex": "Cuántos Rolex te da tu cartera",
    "aceite": "Cuántos litros de aceite de oliva te da tu cartera",
    "paella": "Cuántas paellas para cuatro te da tu cartera",
    "croquetas": "Cuántas raciones de croquetas te da tu cartera",
    "pan": "Cuántas barras de pan te da tu cartera",
    "emoji": "Cómo va tu cartera hoy, en una cara",
    "tiempo": "Cómo va tu cartera hoy, como en el parte del tiempo",
    "carnet": "Cuántos carnets de conducir te da tu cartera",
    "navidad": "Los días que faltan para Navidad y tu cartera en cestas",
    "nochevieja": "Lo que queda de año y tu cartera en botellas de cava",
    "tendencias": "Las que más se buscan hoy, y aviso si sale una tuya",
    "top": "Las 5 que más suben y las 5 que más bajan hoy",
    "altseason": "Si es temporada de altcoins: cuántas le ganan a bitcoin en 30 días",
    "mapa": "Las 30 más grandes en recuadros, en verde o en rojo según su día",
    "sectores": "Qué tipo de cripto sube hoy: memes, IA, DeFi...",
    "aleatoria": "Una de las 100 más grandes al azar, para descubrir alguna",
    "caraocruz": "¿Compro o vendo? Una moneda al aire (ej: /caraocruz btc)",
    "dado": "Qué hacer con tu cripto, a lo que diga un dado (ej: /dado sol)",
    "adivina": "Adivina a cuánto está y te digo si te acercas (ej: /adivina 70000)",
    "ppt": "Piedra, papel o tijera contra mí, y el que gane decide (ej: /ppt piedra)",
    "frase": "Una frase famosa del mundo cripto, al azar",
    "consejo": "Un consejo de inversión malísimo, de broma",
    "excusa": "Una excusa para cuando la cartera va mal, de broma",
    "refran": "Un refrán de toda la vida, versión cripto",
    "horoscopo": "Tu horóscopo cripto de hoy (ej: /horoscopo aries)",
    "galleta": "Tu galleta de la suerte del día, con números",
    "tarot": "Saca una carta del tarot cripto, de broma",
    "bola": "La bola mágica contesta lo que le preguntes (ej: /bola ¿vendo?)",
    "chiste": "Un chiste de cripto, al azar",
    "dato": "Un dato curioso de cripto, al azar",
    "quiz": "Una pregunta de cripto con tres respuestas para pulsar",
    "glosario": "Qué significa hodl, fomo, dca... (ej: /glosario fomo)",
    "miedo": "El índice de miedo y codicia del mercado",
    "sesgo": "Si compras con miedo o con codicia, y cómo te ha ido",
    "comisionred": "Lo que cuesta mover bitcoin, y aviso al bajar (ej: /comisionred 5)",
    "dificultad": "Cuándo toca el próximo ajuste de bitcoin y si entran mineros",
    "hashribbons": "Si los mineros de bitcoin están capitulando (hash ribbons)",
    "lightning": "Cuánto bitcoin hay en Lightning y si la red crece o encoge",
    "direccion": "Vigila una dirección de bitcoin o ethereum y avisa si se mueve",
    "funding": "Si los de futuros apuestan a que sube o baja (ej: /funding btc)",
    "oi": "Cuánto hay apostado en futuros y si entra o sale (ej: /oi btc)",
    "longshort": "Cuántos apuestan a que sube y a que baja (ej: /longshort btc)",
    "profundidad": "Cuánto dinero hace falta para moverla un 2% (ej: /profundidad btc)",
    "premium": "Si en Coinbase pagan más que en Binance: si compra EE. UU.",
    "kimchi": "Lo que se paga de más por bitcoin en Corea (ej: /kimchi btc)",
    "spread": "El precio de CoinGecko contra el de Binance (ej: /spread btc eth)",
    "buscar": "Encuentra el id de una cripto (ej: /buscar btc)",
    "copia": "Lo que vigilo y tu cartera, listo para pegar en el .env",
    "ajustes": "Lo que tienes puesto: moneda, horas tranquilas, avisos...",
    "consultas": "Cuántas consultas a CoinGecko llevas este mes",
    "invitar": "Un código para que otra persona use el bot con sus cosas",
    "usuarios": "A quién has invitado, con un botón para quitarlo",
    "expulsar": "Quita a un invitado (mejor desde /usuarios)",
    "mute": "Callar los avisos un rato (ej: /mute 2h o /mute bitcoin hasta 8:00)",
    "unmute": "Volver a avisar",
    "bot": "Si sigo funcionando: desde cuándo y el último ciclo",
    "version": "Qué versión del bot está corriendo",
    "ayuda": "Lo que sé hacer",
}

# Telegram no deja meter más de 100 en el menú y con todos lo rechaza entero.
# Pongo los de diario; el resto se escriben igual y salen en /ayuda.
MENU = {
    nombre: COMANDOS[nombre]
    for nombre in (
        "status", "precio", "hoy", "resumen", "cartera", "reparto", "semana",
        "mes", "anual", "compra", "venta", "importar", "movimientos", "deshacer",
        "ganancias", "rentabilidad", "impuestos", "alerta", "alertas", "quitar",
        "stop", "vigilar", "dejar", "historico", "comparar", "convertir", "rsi",
        "miedo", "mercado", "top", "equivale", "buscar", "exportar", "backup",
        "mute", "unmute", "ajustes", "bot", "ayuda",
    )
}  # fmt: skip

# /start lo manda Telegram solo la primera vez que abres el chat.
ALIAS = {
    "legado": "herencia",
    "escalon": "escalera",
    "escalones": "escalera",
    "squeeze": "tormenta",
    "emoción": "emocion",
    "sentimientos": "emociones",
    "simulador": "fantasma",
    "practica": "fantasma",
    "predicción": "prediccion",
    "apuesta": "prediccion",
    "clasificacion": "liga",
    "poll": "encuesta",
    "quiniela": "encuesta",
    "clasificación": "liga",
    "momento": "timing",
    "start": "ayuda",
    "invitados": "usuarios",
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
    "staking": "recompensa",
    "airdrop": "recompensa",
    "sell": "venta",
    "historial": "movimientos",
    "semanal": "semana",
    "mensual": "mes",
    "month": "mes",
    "año": "anual",
    "ano": "anual",
    "ytd": "anual",
    "undo": "deshacer",
    "editar": "corregir",
    "corrige": "corregir",
    "alert": "alerta",
    "alerts": "alertas",
    "watch": "vigilar",
    "estado": "status",
    "p": "precio",
    "target": "objetivo",
    "goal": "meta",
    "promedio": "promediar",
    "tamano": "posicion",
    "ahorro": "plan",
    "interes": "apy",
    "límite": "limite",
    "presupuesto": "limite",
    "interés": "apy",
    "tamaño": "posicion",
    "posición": "posicion",
    "maximo": "ath",
    "trending": "tendencias",
    "moda": "tendencias",
    "suben": "top",
    "temporada": "altseason",
    "calor": "mapa",
    "sector": "sectores",
    "narrativas": "sectores",
    "heatmap": "mapa",
    "altcoinseason": "altseason",
    "bajan": "top",
    "codicia": "miedo",
    "humor": "sesgo",
    "fear": "miedo",
    "mempool": "comisionred",
    "hashrate": "dificultad",
    "ribbons": "hashribbons",
    "mineros": "hashribbons",
    "capitulacion": "hashribbons",
    "capitulación": "hashribbons",
    "ln": "lightning",
    "rayo": "lightning",
    "mineria": "dificultad",
    "minería": "dificultad",
    "dirección": "direccion",
    "direcciones": "direccion",
    "monedero": "direccion",
    "financiacion": "funding",
    "interesabierto": "oi",
    "largos": "longshort",
    "liquidez": "profundidad",
    "prima": "premium",
    "corea": "kimchi",
    "ordenes": "profundidad",
    "órdenes": "profundidad",
    "cortos": "longshort",
    "openinterest": "oi",
    "meses": "estacional",
    "estacionalidad": "estacional",
    "multiplo": "mayer",
    "arcoíris": "arcoiris",
    "rainbow": "arcoiris",
    "200semanas": "suelo",
    "200w": "suelo",
    "pi": "picycle",
    "techo": "picycle",
    "ahr": "ahr999",
    "aguante": "paciencia",
    "hueco": "cme",
    "gap": "cme",
    "vix": "dvol",
    "opciones": "dvol",
    "vencimiento": "maxpain",
    "dolor": "maxpain",
    "múltiplo": "mayer",
    "financiación": "funding",
    "comisiónred": "comisionred",
    "market": "mercado",
    "compare": "comparar",
    "volatility": "volatilidad",
    "falsos": "ruido",
    "enfalso": "ruido",
    "range": "rango",
    "streak": "racha",
    "rojos": "verdes",
    "mejor": "extremo",
    "peor": "extremo",
    "drawdown": "caida",
    "sobrecompra": "rsi",
    "semáforo": "semaforo",
    "señal": "semaforo",
    "bandas": "bollinger",
    "empuje": "macd",
    "estocástico": "estocastico",
    "stoch": "estocastico",
    "fibo": "fibonacci",
    "inflación": "inflacion",
    "ipc": "inflacion",
    "retroceso": "fibonacci",
    "dominance": "dominancia",
    "altcoins": "dominancia",
    "proyeccion": "futuro",
    "proyección": "futuro",
    "cuándo": "cuando",
    "when": "cuando",
    "día": "dia",
    "fecha": "dia",
    "respaldo": "backup",
    "backfill": "rellenar",
    "rellena": "rellenar",
    "tarta": "reparto",
    "rebalancear": "rebalanceo",
    "desvio": "ideal",
    "desvío": "ideal",
    "tir": "rentabilidad",
    "anualizada": "rentabilidad",
    "rebalance": "rebalanceo",
    "pesos": "reparto",
    "correlación": "correlacion",
    "correlation": "correlacion",
    "env": "copia",
    "caída": "caida",
    "subida": "sube",
    "today": "hoy",
    "hours": "horas",
    "weekday": "diasemana",
    "soportes": "soporte",
    "resistencia": "soporte",
    "resistencias": "soporte",
    "diadelmes": "diames",
    "breakeven": "equilibrio",
    "x2": "doble",
    "first": "primera",
    "mote": "apodo",
    "cheque": "enletras",
    "letras": "enletras",
    "diamante": "hodl",
    "aguantar": "hodl",
    "récord": "record",
    "pico": "record",
    "vsbitcoin": "vsbtc",
    "contrabtc": "vsbtc",
    "depósito": "deposito",
    "comision": "comisiones",
    "comisión": "comisiones",
    "fees": "comisiones",
    "banco": "deposito",
    "café": "cafe",
    "coffee": "cafe",
    "salario": "sueldo",
    "smi": "sueldo",
    "salary": "sueldo",
    "gasoil": "gasolina",
    "gas": "gasolina",
    "burger": "bigmac",
    "hamburguesa": "bigmac",
    "playstation": "ps5",
    "nintendo": "switch",
    "peli": "cine",
    "pelis": "cine",
    "movie": "cine",
    "gym": "gimnasio",
    "gimnasios": "gimnasio",
    "vuelos": "vuelo",
    "viaje": "vuelo",
    "avion": "vuelo",
    "avión": "vuelo",
    "supermercado": "super",
    "carro": "super",
    "kebabs": "kebab",
    "doner": "kebab",
    "döner": "kebab",
    "abono": "metro",
    "transporte": "metro",
    "bus": "metro",
    "factura": "luz",
    "electricidad": "luz",
    "libros": "libro",
    "leer": "libro",
    "conciertos": "concierto",
    "musica": "concierto",
    "música": "concierto",
    "auriculares": "airpods",
    "cascos": "airpods",
    "zapas": "zapatillas",
    "sneakers": "zapatillas",
    "tren": "ave",
    "barcelona": "ave",
    "menú": "menu",
    "comida": "menu",
    "noche": "hotel",
    "noches": "hotel",
    "peluquería": "peluqueria",
    "pelo": "peluqueria",
    "barberia": "peluqueria",
    "portatil": "macbook",
    "portátil": "macbook",
    "mac": "macbook",
    "bicicleta": "bici",
    "bicis": "bici",
    "churro": "churros",
    "chocolate": "churros",
    "lotería": "loteria",
    "decimo": "loteria",
    "décimo": "loteria",
    "pisos": "piso",
    "casa": "piso",
    "vivienda": "piso",
    "fútbol": "futbol",
    "partido": "futbol",
    "estadio": "futbol",
    "taxis": "taxi",
    "aeropuerto": "taxi",
    "cabify": "taxi",
    "pincho": "tortilla",
    "tortillas": "tortilla",
    "videojuegos": "videojuego",
    "juego": "videojuego",
    "juegos": "videojuego",
    "sofá": "sofa",
    "sofas": "sofa",
    "sofás": "sofa",
    "ikea": "sofa",
    "coches": "coche",
    "auto": "coche",
    "bodas": "boda",
    "casarse": "boda",
    "jamón": "jamon",
    "jamones": "jamon",
    "aove": "aceite",
    "oliva": "aceite",
    "paellas": "paella",
    "croqueta": "croquetas",
    "barras": "pan",
    "reloj": "rolex",
    "cara": "emoji",
    "clima": "tiempo",
    "parte": "tiempo",
    "animo": "emoji",
    "ánimo": "emoji",
    "carne": "carnet",
    "autoescuela": "carnet",
    "cesta": "navidad",
    "christmas": "navidad",
    "xmas": "navidad",
    "findeaño": "nochevieja",
    "findeano": "nochevieja",
    "uvas": "nochevieja",
    "caña": "cana",
    "cañas": "cana",
    "cerveza": "cana",
    "birra": "cana",
    "beer": "cana",
    "ganancia": "ganancias",
    "arrepentida": "arrepentido",
    "regret": "arrepentido",
    "beneficios": "ganancias",
    # /maximo ya es /ath; el mínimo del tramo sale en lo primero de /sube.
    "minimo": "sube",
    "mínimo": "sube",
    "average": "media",
    "ranking": "comparar",
    "quieto": "quieta",
    "calma": "quieta",
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
    "jugar": "ppt",
    "adivinar": "adivina",
    "guess": "adivina",
    "cita": "frase",
    "quote": "frase",
    "consejos": "consejo",
    "tip": "consejo",
    "excusas": "excusa",
    "refrán": "refran",
    "refranes": "refran",
    "dicho": "refran",
    "horóscopo": "horoscopo",
    "fortuna": "galleta",
    "carta": "tarot",
    "bola8": "bola",
    "broma": "chiste",
    "curiosidad": "dato",
    "trivial": "quiz",
    "pregunta": "quiz",
    "sabias": "dato",
    "chistes": "chiste",
    # Sin "hodl": se parece tanto a "hola" que a un saludo le sugería /glosario.
    "glossary": "glosario",
    "diccionario": "glosario",
    "sats": "sat",
    "whale": "ballena",
    "satoshi": "sat",
    "summary": "resumen",
    "schedule": "horario",
    "tranquilas": "dormir",
    "vivo": "envivo",
    "live": "envivo",
    "fijado": "envivo",
    "week": "semana",
    "transactions": "movimientos",
    "profit": "ganancias",
    "pnl": "ganancias",
    "hacienda": "impuestos",
    "irpf": "impuestos",
    "taxes": "impuestos",
    "pdf": "informe",
    "gestor": "informe",
    "sivender": "sivendo",
    "swap": "permuta",
    "721": "modelo721",
    "compartir": "tarjeta",
    "bolsa": "vsbolsa",
    "sp500": "vsbolsa",
    "intercambiar": "permuta",
    "compensa": "compensar",
    "perdidas": "compensar",
    "pérdidas": "compensar",
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
    "versión": "version",
    "millon": "millonario",
    "millón": "millonario",
    "cumpleaños": "cumple",
    "edad": "cumple",
    "paper": "whitepaper",
}


def _lista(ocultas: frozenset[str] = frozenset()) -> str:
    # Las de /equivale no salen una a una: eran 48 líneas de "cuántos X te da".
    return (
        "🤖 <b>Esto es lo que sé hacer</b>\n\n"
        + "\n".join(
            f"/{nombre} — {texto}"
            for nombre, texto in COMANDOS.items()
            if nombre not in equivale.COSAS and nombre not in ocultas
        )
        + "\n\nCon ejemplos de uno: /ayuda alerta"
        + "\nTambién sin barra: «avísame si btc baja de 60000», «cuánto vale eth», "
        "«cómo va mi cartera» o «cállate 2 horas»."
    )


AYUDA = _lista()


def _lista_tema(tema: temas.Tema, ocultas: frozenset[str]) -> str:
    nombres = temas.visibles(tema, ocultas)
    lineas = [f"/{c} — {COMANDOS[c]}" for c in nombres]
    return (
        f"<b>{tema.titulo}</b>\n\n"
        + "\n".join(lineas)
        + f"\n\nCon ejemplos de uno: /ayuda {nombres[0]}"
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
        ("/alerta bitcoin 60000 o 80000", "la que llegue antes, y quito la otra"),
        ("/alerta bitcoin 70000 vender la mitad", "con una nota para el aviso"),
        ("/alerta cartera 5000", "con lo que vale tu cartera entera"),
        ("/alerta eth/btc 0.05", "cuando un ethereum valga eso en bitcoin"),
        ("/alerta bitcoin", "sin precio, te digo a cuánto está"),
    ],
    "stop": [
        ("/stop eth -15%", "si pierdes un 15% sobre tu precio medio"),
        ("/stop btc +50%", "si ganas un 50%"),
        ("/stop cartera -20%", "con todo lo que metiste en la cartera"),
        ("/stop btc -10% movil", "si cae un 10% desde lo más alto que toque"),
    ],
    "escalera": [
        ("/escalera btc 80000 90000 100000", "vender un tercio en cada precio"),
        ("/escalera btc 80k 90k 50%", "solo la mitad de lo que tienes"),
        ("/escalera compra btc 60k 55k 50k con 900", "300 en cada bajada"),
        ("/escalera compra eth 2000 1800", "solo el aviso, sin decir cuánto"),
    ],
    "anual": [
        ("/anual", "cómo va tu cartera desde el 1 de enero, con gráfica"),
        ("/anual 2025", "el resumen de ese año: mejor mes, compras, ventas…"),
        ("/anual 2025 tarjeta", "en una imagen para enseñar, solo con %"),
    ],
    "tendencias": [
        ("/tendencias", "las que más se buscan hoy en CoinGecko"),
        ("/tendencias avisa", "te aviso si entra una de las tuyas"),
        ("/tendencias avisa no", "dejar de avisarte"),
    ],
    "tesis": [
        ("/tesis sol el ETF lo va a subir", "te pregunto a los 30 días"),
        ("/tesis btc 90d se acaba la sequía", "a los 90 días"),
        ("/tesis", "las que tienes y cuántas aciertas"),
        ("/tesis si 3", "la 3 se cumplió (o /tesis no 3)"),
        ("/tesis quitar 3", "borrarla"),
    ],
    "herencia": [
        ("/herencia", "el papel en un .txt para guardar o imprimir"),
        ("/herencia btc Ledger en el cajón", "dónde está cada una, nunca la clave"),
        ("/herencia nota Habla con mi hermana", "una nota para quien lo lea"),
        ("/herencia btc no", "quitar dónde está"),
    ],
    "fantasma": [
        ("/fantasma", "cómo va, contra dejarlo todo en bitcoin"),
        ("/fantasma compra btc 200", "gastar 200 de mentira en bitcoin"),
        ("/fantasma vende btc 50%", "también 'todo' o un importe"),
        ("/fantasma reinicia 5000", "empezar de cero (sin cifra, con 1.000)"),
    ],
    "juntas": [
        ("/juntas btc eth", "te aviso si dejan de moverse a la vez"),
        ("/juntas", "las parejas que miro"),
        ("/juntas btc eth no", "quitarla"),
    ],
    "encuesta": [
        ("/encuesta", "te mando una ya y luego una cada lunes"),
        ("/encuesta no", "quitarla"),
    ],
    "liga": [
        ("/liga", "la clasificación desde el principio"),
        ("/liga semana", "solo la del último domingo"),
    ],
    "prediccion": [
        ("/prediccion btc 70000", "a cuánto estará el domingo a las 20:00"),
        ("/prediccion", "lo que tienes en juego y tu marcador"),
        ("/prediccion btc no", "quitar la que aún no ha llegado"),
    ],
    "pienso": [
        ("/pienso btc 500", "lo que hay ahora, y mañana te pregunto otra vez"),
        ("/pienso", "lo que te estás pensando"),
        ("/pienso btc no", "olvidarlo"),
    ],
    "rezagada": [
        ("/rezagada eth btc 10", "si ethereum va un 10% peor que bitcoin en 7 días"),
        ("/rezagada", "las que tienes puestas"),
        ("/rezagada eth btc no", "quitarla"),
    ],
    "cada": [
        ("/cada viernes 20:00 /cartera", "cada viernes, tu cartera sin pedirla"),
        ("/cada dia 9:00 /precio btc", "todos los días"),
        ("/cada", "lo que tienes programado"),
        ("/cada quitar 1", "quitar el número 1"),
    ],
    "recordar": [
        ("/recordar lunes 50 btc", "cada lunes, con un botón para apuntarla"),
        ("/recordar", "los que tienes puestos"),
        ("/recordar btc no", "dejar de recordarlo"),
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
    "ideal": [
        ("/ideal btc 60 eth 40", "te aviso cuando alguna se aleje 5 puntos"),
        ("/ideal btc 60 eth 40 margen 10", "con otro margen"),
        ("/ideal", "a secas, cómo vas contra tu reparto"),
        ("/ideal no", "quitarlo"),
    ],
    "rebalanceo": [
        ("/rebalanceo btc 60 eth 40", "qué mover para quedarte con ese reparto"),
        ("/rebalanceo btc 100", "lo que no nombres, a venderlo entero"),
        ("/rebalanceo", "a secas, a partes iguales entre lo que tienes"),
    ],
    "corregir": [
        ("/corregir 12 cantidad 0.02", "el número sale en /movimientos"),
        ("/corregir 12 importe 700", "lo que pagaste o te dieron en total"),
        ("/corregir 12 importe @60000", "con el precio de cada una"),
    ],
    "recompensa": [
        ("/recompensa eth 0.02", "lo que te ha llegado, al precio de ahora"),
        ("/recompensa eth 0.02 50", "si te llegó antes, con lo que valía entonces"),
        ("/recompensa eth 0.02 staking de octubre", "con una nota"),
    ],
    "compra": [
        ("/compra bitcoin 0.01 600", "0,01 por 600 € en total"),
        ("/compra bitcoin 0.01 @60000", "con el precio de cada una"),
        ("/compra bitcoin 0.01 600 com 1.5", "con 1,5 € de comisión, o com 0.1%"),
        ("/compra bitcoin 0.01 600 por el halving", "con una nota de por qué"),
    ],
    "venta": [
        ("/venta bitcoin 0.005 350", "una parte, por 350 € en total"),
        ("/venta bitcoin 0.005 @70000", "con el precio de cada una"),
        ("/venta bitcoin 0.005", "sin precio, al de ahora"),
        ("/venta bitcoin todo", "la saca de la cartera"),
        ("/venta bitcoin 0.005 350 com 1", "se resta de lo que te dieron"),
    ],
    "historico": [
        ("/historico bitcoin", "gráfica de las últimas 24 h"),
        ("/historico bitcoin 7d", "del tramo que digas (12h, 7d, 30d...)"),
        ("/historico bitcoin 7d velas", "en velas: verde si cerró más alto"),
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
        ("/correlacion todas", "todas contra todas, en una imagen"),
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
        ("/racha cartera", "lo mismo con tu cartera entera"),
    ],
    "extremo": [
        ("/extremo bitcoin", "el día que más subió y el que más bajó en 30 días"),
        ("/extremo bitcoin 7d", "del tramo que digas"),
        ("/extremo", "a secas, la primera que vigilo"),
    ],
    "calendario": [
        ("/calendario bitcoin", "este mes, cada día en verde o en rojo"),
        ("/calendario bitcoin octubre", "un mes que ya ha pasado"),
        ("/calendario", "a secas, la primera que vigilo"),
    ],
    "verdes": [
        ("/verdes bitcoin", "cuántos días subió y cuántos bajó en 30 días"),
        ("/verdes bitcoin 7d", "del tramo que digas"),
        ("/verdes", "a secas, la primera que vigilo"),
    ],
    "diames": [
        ("/diames bitcoin", "qué día del mes ha salido más barata en el último año"),
        ("/diames bitcoin 180d", "del tramo que digas"),
        ("/diames", "a secas, la primera que vigilo"),
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
    "comisionred": [
        ("/comisionred", "lo que cuesta ahora, con prisa y sin ella"),
        ("/comisionred 5", "te aviso una vez cuando baje a 5 sat/vB"),
        ("/comisionred no", "quitar el aviso"),
    ],
    "informe": [
        ("/informe", "el PDF de este año: resumen, cuota y cada venta"),
        ("/informe 2025", "el de otro año"),
    ],
    "impuestos": [
        ("/impuestos", "lo de este año, por tramos"),
        ("/impuestos 2025", "el año que digas"),
        ("/impuestos 2025 csv", "cada venta en un archivo, para la Renta"),
    ],
    "sivendo": [
        ("/sivendo btc 0.005", "al precio de ahora"),
        ("/sivendo btc todo", "todo lo que tienes"),
        ("/sivendo btc 0.005 @80000", "si la vendes a ese precio"),
    ],
    "vsbolsa": [
        ("/vsbolsa", "contra un indexado del S&P 500"),
        ("/vsbolsa world", "contra el MSCI World, todo el mundo"),
    ],
    "permuta": [
        ("/permuta btc eth 0.01", "cambiar 0,01 bitcoin por ethereum"),
        ("/permuta btc eth todo", "todo lo que tienes"),
        ("/permuta btc eth 0.01 com 0.1%", "con la comisión del exchange"),
    ],
    "exportar": [
        ("/exportar bitcoin 30d", "los precios guardados de ese tramo"),
        ("/exportar movimientos", "todas tus compras y ventas, para tu gestor"),
    ],
    "rellenar": [
        ("/rellenar", "las que vigilo, hasta donde guardo"),
        ("/rellenar btc eth", "solo esas"),
        ("/rellenar btc 30d", "solo ese tramo"),
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
    "soporte": [
        ("/soporte bitcoin", "dónde ha girado varias veces en 90 días"),
        ("/soporte bitcoin 30d", "del tramo que digas"),
        ("/soporte", "a secas, la primera que vigilo"),
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
    "direccion": [
        ("/direccion bc1q... frío", "la vigila con ese nombre y avisa si se mueve"),
        ("/direccion 0x... ledger", "lo mismo con una de ethereum"),
        ("/direccion", "las que vigilo, con lo que tiene cada una"),
        ("/direccion quitar frío", "deja de vigilarla"),
    ],
    "estacional": [
        ("/estacional btc", "cada mes desde 2017, y si sube más de lo que baja"),
        ("/estacional", "a secas, la primera que vigilo"),
    ],
    "maxpain": [
        ("/maxpain", "el vencimiento de este viernes en bitcoin"),
        ("/maxpain eth", "el de ethereum"),
    ],
    "dvol": [
        ("/dvol", "el de bitcoin y cuánto esperan que se mueva"),
        ("/dvol eth", "el de ethereum"),
    ],
    "paciencia": [
        ("/paciencia", "bitcoin: a 1 mes, 6 meses y hasta 4 años"),
        ("/paciencia eth", "lo mismo con otra"),
    ],
    "mayer": [
        ("/mayer", "el de bitcoin, y en qué parte de su historia está"),
        ("/mayer eth", "el de otra, aunque se pensó para bitcoin"),
    ],
    "spread": [
        ("/spread btc eth", "lo que da cada uno de esas y cuánto se separan"),
        ("/spread", "a secas, las que vigilo"),
    ],
    "invitar": [
        ("/invitar", "un código de un solo uso que caduca en 24 h"),
    ],
    "oi": [
        ("/oi btc", "lo apostado en futuros de Binance y cómo ha cambiado"),
        ("/oi", "a secas, la primera que vigilo"),
    ],
    "kimchi": [
        ("/kimchi", "lo que se paga de más por bitcoin en Corea"),
        ("/kimchi eth", "lo mismo con otra que esté en Upbit y en Binance"),
    ],
    "premium": [
        ("/premium", "lo que se paga de más por bitcoin en Coinbase"),
        ("/premium eth", "lo mismo con otra que esté en los dos"),
    ],
    "profundidad": [
        ("/profundidad btc", "lo que costaría moverla un 0,5, un 1 y un 2%"),
        ("/profundidad", "a secas, la primera que vigilo"),
    ],
    "longshort": [
        ("/longshort btc", "cuántos apuestan a cada lado en los futuros de Binance"),
        ("/longshort", "a secas, la primera que vigilo"),
        ("/longshort btc avisa", "te aviso si se va más gente de lo normal a un lado"),
        ("/longshort btc no", "quitar el aviso"),
    ],
    "funding": [
        ("/funding btc", "lo que pagan los de futuros de bitcoin y si está apalancado"),
        ("/funding", "a secas, la primera que vigilo"),
        ("/funding btc avisa", "te aviso cuando se vaya a un extremo"),
        ("/funding btc no", "quitar ese aviso"),
    ],
    "sharpe": [
        ("/sharpe", "los últimos 90 días, comparado con bitcoin"),
        ("/sharpe 365d", "de 30 a 365 días"),
    ],
    "futuro": [
        ("/futuro", "entre qué cifras puede estar tu cartera dentro de 30 días"),
        ("/futuro 90d", "de 1 a 365 días"),
    ],
    "fibonacci": [
        ("/fibonacci btc", "los niveles entre el máximo y el mínimo de 90 días"),
        ("/fibonacci btc 30d", "en otro tramo"),
    ],
    "macd": [
        ("/macd bitcoin", "si va con empuje al alza o a la baja y desde cuándo"),
        ("/macd", "a secas, la primera que vigilo"),
    ],
    "ruido": [
        ("/ruido", "todas las que vigilo, en los últimos 30 días"),
        ("/ruido bitcoin 90d", "solo una y en otro tramo"),
    ],
    "estocastico": [
        (
            "/estocastico bitcoin",
            "si está cerca de lo más alto o lo más bajo de 14 días",
        ),
        ("/estocastico", "a secas, la primera que vigilo"),
    ],
    "bollinger": [
        ("/bollinger bitcoin", "si está dentro de su banda de 20 días o se ha salido"),
        ("/bollinger", "a secas, la primera que vigilo"),
    ],
    "semaforo": [
        ("/semaforo bitcoin", "verde, ámbar o rojo, y qué dice cada indicador"),
        ("/semaforo", "a secas, la primera que vigilo"),
    ],
    "rsi": [
        ("/rsi bitcoin", "el RSI de 14 días: por encima de 70 sobrecomprada"),
        ("/rsi", "a secas, la primera que vigilo"),
    ],
    "tarjeta": [
        ("/tarjeta", "cómo va tu cartera y los últimos 30 días"),
        ("/tarjeta 90d", "con el tramo que digas"),
    ],
    "backtest": [
        ("/backtest btc", "vender al +20% y recomprar al -20%, en 90 días"),
        ("/backtest btc 10%", "con el % que digas"),
        ("/backtest btc 15% 30d", "y el tramo que digas"),
    ],
    "caida": [
        ("/caida bitcoin", "cuánto ha bajado desde el máximo de 30 días"),
        ("/caida bitcoin 7d", "del tramo que digas"),
        ("/caida cartera 90d", "lo mismo con lo que vale tu cartera entera"),
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
    "promediar": [
        ("/promediar bitcoin 50000", "cuánto comprar hoy para que te salga a 50.000"),
        ("/promediar eth 2k", "también vale con k o con el €"),
    ],
    "posicion": [
        ("/posicion 1000 2% -10%", "con 1.000, perder como mucho un 2% si cae un 10%"),
        ("/posicion btc 1000 2% -10%", "lo mismo, en bitcoin y con el precio del stop"),
        ("/posicion btc 1000 2% 58000", "con la cripto, el stop puede ser un precio"),
    ],
    "limite": [
        ("/limite 300", "te aviso al comprar si este mes pasas de 300"),
        ("/limite", "cuánto llevas este mes"),
        ("/limite no", "lo quita"),
    ],
    "apy": [
        ("/apy eth 4%", "lo que tendrías de tu ethereum en 1, 3, 5 y 10 años"),
        ("/apy 2 eth 4%", "con la cantidad que digas, aunque no la tengas"),
        ("/apy eth 4% 5a", "solo a esos años"),
    ],
    "comisiones": [
        ("/comisiones", "todo lo que llevas pagado, por año y por cripto"),
        ("/comisiones 2025", "solo las de ese año"),
    ],
    "deposito": [
        ("/deposito", "tu cartera contra un depósito al 3% al año"),
        ("/deposito 2,5%", "con el interés que digas"),
    ],
    "plan": [
        ("/plan 10000 50", "cuánto tardas en llegar a 10.000 metiendo 50 cada semana"),
        ("/plan 10000 200 mensual", "también diario o mensual"),
        ("/plan 10000 50 semanal 8%", "suponiendo que dé un 8% al año"),
    ],
    "meta": [
        ("/meta 10000", "cuánto le falta a tu cartera para llegar a 10.000"),
        ("/meta 10k", "también vale con k o con el €"),
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
    "dormir": [
        ("/dormir", "las horas en que no suenan"),
        ("/dormir 23-8", "cambiarlas"),
        ("/dormir no", "que suenen siempre"),
    ],
    "envivo": [
        ("/envivo", "lo pongo y lo fijo arriba; si ya estaba, lo bajo al final"),
        ("/envivo no", "quitarlo"),
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


INICIO = (
    "🤖 <b>¿Qué quieres hacer?</b> Elige un tema.\n\n"
    "Para empezar: /status, /precio btc o /alerta btc 70000\n"
    "De uno en concreto, con ejemplos: /ayuda alerta\n"
    "También sin barra: «avísame si btc baja de 60000» o «cuánto vale eth»."
)

VOLVER = [[("⬅️ Otros temas", "/ayuda")]]


def ayuda(
    argumento: str = "", ocultas: frozenset[str] = frozenset()
) -> "str | ConBotones":
    """/ayuda a secas, los temas. /ayuda avisos, los de ese tema. /ayuda alerta,
    ese con sus ejemplos. /ayuda todo, la lista entera como antes.

    ocultas son los que no puede usar quien pregunta: a un invitado no le
    enseño /invitar ni /binance."""
    if not argumento.strip():
        return ConBotones(INICIO, temas.botones(ocultas))
    if argumento.strip().lower() == temas.TODO:
        return _lista(ocultas) if ocultas else AYUDA
    tema = temas.buscar(argumento)
    if tema:
        return ConBotones(_lista_tema(tema, ocultas), VOLVER)

    pedido = argumento.split()[0].lstrip("/").lower()
    nombre = ALIAS.get(pedido, pedido)
    if nombre in ocultas:
        return "Eso solo lo puede usar quien lleva el bot."
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
        if _son_criptos(texto):
            return "precio", texto.strip()
        return lenguaje.entender(texto)

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
