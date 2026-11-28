# Instalación y configuración

[← Volver al README](../README.md)

## Lo que necesitas

- Un ordenador o servidor con **Python 3.10 o superior** ([descargar](https://www.python.org/downloads/))
- Telegram

---

## Instalación

**1. Descarga el proyecto y ábrelo en una terminal.**

**2. Prepara el entorno:**

Windows:
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Mac o Linux:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Crear el bot de Telegram

Necesitas dos datos: el **token** del bot y tu **chat id**.

**El token:**

1. Abre Telegram y busca **@BotFather**
2. Escríbele `/newbot`
3. Te pide un nombre y un usuario para el bot
4. Te da un texto largo tipo `123456789:AAxxxxxx...` — ese es el token

**Tu chat id:**

1. Busca **@userinfobot** en Telegram
2. Escríbele cualquier cosa
3. Te contesta con un número — ese es tu chat id

**Importante:** busca el bot que acabas de crear y escríbele `/start`. Si no lo
haces, Telegram no le deja mandarte mensajes.

**Opcional, para mandar precios a otros chats:** escríbele `/setinline` a
@BotFather, elige tu bot y pon un texto cualquiera (por ejemplo `btc eth`). Así
puedes escribir `@tubot btc` en cualquier conversación.

---

## La clave de CoinGecko

Es gratis y evita que CoinGecko te bloquee las consultas de precios, cosa que
sin clave pasa con bastantes conexiones.

1. Entra en [coingecko.com/en/api/pricing](https://www.coingecko.com/en/api/pricing)
   y elige el plan **Demo** (gratis)
2. Regístrate y, en tu panel, crea una clave. Empieza por `CG-`
3. Luego la pegas en `COINGECKO_API_KEY` del `.env`

---

## Configuración

Copia el archivo de ejemplo:

Windows: `copy .env.example .env`
Mac/Linux: `cp .env.example .env`

Abre el `.env` con cualquier editor de texto y rellena el token y el chat id.

Luego elige qué criptos vigilar en la línea `WATCHLIST`. Hay tres formas:

**Avisarte cada vez que pase un múltiplo:**
```
WATCHLIST=bitcoin:1000
```
Te avisa cuando Bitcoin pase por 63.000, luego por 64.000, luego por 65.000...

**Avisarte cuando se mueva un porcentaje:**
```
WATCHLIST=bitcoin:%5
```
Te avisa cada vez que suba o baje un 5% desde el último aviso. Va por tramos: si
sube un 12% de golpe te avisa una vez, y vuelve a avisarte al siguiente 5%.

Suele ser la más útil: un paso de 1.000 € no significa lo mismo con Bitcoin a
30.000 que a 120.000, y un porcentaje sí.

**Avisarte al salir de un rango:**
```
WATCHLIST=bitcoin:55000:75000
```
Te avisa si baja de 55.000 o si sube de 75.000.

Cada aviso lleva debajo cuánto ha variado en las últimas 24 h (`En 24 h: 🔺
+4.17%`), para saber si viene de un subidón o es ruido, y cuánto le falta para
su máximo histórico.

Si en 24 h se ha movido un 3% o más, añade qué pasó las otras veces que se movió
parecido en un día, con lo que tiene guardado: `En 90 días cayó más de un 4.0% en
un día 3 veces: a la semana estaba +1.7% de media y en 2 de 3 siguió bajando`.
Con menos de tres casos no lo pone, que sería casualidad.

**Puedes mezclar y poner varias separadas por comas:**
```
WATCHLIST=bitcoin:%5,ethereum:100,solana:5
```

Los nombres son los de CoinGecko: `bitcoin`, no `BTC`. Si no sabes cuál es,
búscalo:
```
python main.py --buscar btc
```
Te saca los candidatos con el más probable primero. Funciona aunque todavía no
hayas rellenado el `.env`.

---

## Probar que funciona

```
python main.py --test
```

Si te llega un mensaje a Telegram, ya está todo bien. Si no, revisa el token, el
chat id, y que le hayas escrito `/start` al bot.

---

## Otras opciones del `.env`

| Opción | Qué hace | Por defecto |
|---|---|---|
| `COINGECKO_API_KEY` | Clave gratuita de CoinGecko (ver arriba) | vacío |
| `BINANCE_API_KEY` y `BINANCE_API_SECRET` | Clave de Binance de solo lectura, para `/binance` | vacío |
| `VS_CURRENCY` | Moneda de los precios (`usd`, `eur`, `gbp`) | `eur` |
| `CHECK_INTERVAL` | Segundos entre consulta y consulta | `330` (5 min y medio) |
| `HISTORY_DAYS` | Días de histórico que se guardan | `90` |
| `DATABASE_PATH` | Dónde se guardan los datos | `data/prices.db` |
| `RESUMEN_DIARIO` | Hora del resumen de cada día (`09:00`), que acaba con el índice de miedo y codicia. Vacío, sin resumen | vacío |
| `MOVIMIENTO_BRUSCO` | Aviso si se mueve mucho en poco tiempo (`8%/1h`). Vacío, sin aviso | vacío |
| `MAXIMOS_MINIMOS` | Aviso al marcar el máximo o mínimo de esos días (`30d`). Vacío, sin aviso | vacío |
| `HORAS_TRANQUILAS` | Tramo en que los avisos llegan sin sonar (`23-8`) | vacío |
| `PORTFOLIO` | Lo que tienes, para ver cuánto vale (`bitcoin:0.016:1000`) | vacío |
| `CAIDA_CARTERA` | Aviso si la cartera cae ese % desde su récord (`20%`). Vacío, sin aviso | vacío |
| `CONCENTRACION` | Aviso si una sola cripto pasa de ese % de la cartera (`70%`, entre 50 y 100). Vacío, sin aviso | vacío |
| `AVISO_RSI` | Con `si`, aviso al entrar en sobrecompra o sobreventa. Vacío, sin aviso | vacío |
| `AVISO_CRUCE` | Con `si`, aviso cuando la media de 50 días cruza la de 200. Necesita `HISTORY_DAYS` de 200 o más. Vacío, sin aviso | vacío |
| `AVISO_VOLUMEN` | Con `si`, aviso cuando el volumen de 24 h pasa del triple de lo normal. Vacío, sin aviso | vacío |
| `AVISO_CALMA` | Con `si`, aviso cuando una lleva una semana mucho más quieta de lo normal. Necesita `HISTORY_DAYS` de 38 o más. Vacío, sin aviso | vacío |
| `COPIA_SEMANAL` | Con `si`, te manda la base de datos cada 7 días. Vacío, sin copia | vacío |
| `LATIDO_URL` | Dirección a la que da un toque en cada consulta que sale bien, para que un servicio de fuera te avise si el bot se muere. Vacío, sin latido | vacío |

No bajes mucho `CHECK_INTERVAL`. La clave gratuita de CoinGecko da 10.000
consultas al mes y cada ciclo gasta una: con `330` (cinco minutos y medio) te
quedan unas 2.000 de margen para `/status`, el resumen y las búsquedas. Con
`300` vas muy justo.

Por si acaso, lleva la cuenta: al pasar del 80 % del mes te avisa, con cómo
acabarías a ese ritmo, y otra vez si llegas al 100 %. Cuenta por mes natural en
UTC, y `/consultas` te dice cómo vas.
